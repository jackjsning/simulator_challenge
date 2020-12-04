"""Pubsub implementation underpinning all IPC logic.

Publishers and subscribers should be instantiated directly by business logic.
"""

import asyncio
import copy
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np  # type: ignore[import]
import pydantic
import redis
from ipc import core, registry

LOGGER = logging.getLogger()


# Redis settings
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_HEALTH_INTERVAL = int(os.environ.get("REDIS_HEALTH_INTERVAL", "30"))  # seconds
REDIS_SUB_SLEEP = float(os.environ.get("REDIS_SUB_SLEEP", "0.0001"))  # seconds

LATENCY_WINDOW_S = 1  # Analyze messages during the past window, seconds


class BasePubSubAgent:
    """Simple common logic for publishers and subscribers.
    """

    def __init__(
        self, node_id: core.NodeID, topic_spec: core.TopicSpec,
    ):
        self._node_id = node_id
        self._topic_spec = topic_spec
        self._redis_client = redis.Redis(
            host=REDIS_HOST,
            port=self._topic_spec.broker_spec.port,
            health_check_interval=REDIS_HEALTH_INTERVAL,
        )  # type: ignore[call-arg]  # Redis types are sometimes out of date


class Publisher(BasePubSubAgent):
    """Provides the ability to publish messages on the given topic.
    """

    def __init__(
        self, node_id: core.NodeID, topic_spec: core.TopicSpec,
    ):
        super().__init__(node_id, topic_spec)
        self._pub_counter = 0

    def publish(self, msg: core.Message) -> None:
        # To make the type checking and hinting simple, we use the base class for our
        # static type, and then do a more specific runtime check.
        if not isinstance(msg, self._topic_spec.msg_cls):
            raise TypeError(f"{type(msg)=}, {self._topic_spec.msg_cls=}")

        # Fill in standard fields for all messages
        msg.sender_id = self._node_id
        msg.pub_dt = datetime.now().astimezone()
        msg.pub_counter = self._pub_counter
        self._pub_counter += 1

        self._redis_client.publish(self._topic_spec.channel, msg.json())


class SubscriberLatencyRecord(pydantic.BaseModel):
    """Simple structured object for tracking high latency issues a subscriber may
    experience.
    """

    msg_rcv_ts: float  # POSIX timestamp for when this message was received
    msg_latency: float  # calculated message latency, seconds


class Subscriber(BasePubSubAgent):
    """Provides the ability to subscribe to the given topic and receive messages.
    Messages may be handled asynchonously via callback or synchronously.

    Also supports various health checks to ensure communications integrity.
    """

    def __init__(
        self,
        node_id: core.NodeID,
        topic: core.TopicSpec,
        async_callback: Optional[Callable],
    ):
        super().__init__(node_id, topic)

        # Not easy to type hint a coroutine function (as opposed to a coroutine), so we
        # check it dynamically
        if async_callback is not None and not asyncio.iscoroutinefunction(
            async_callback
        ):
            raise TypeError("Expecting coroutine function")
        self._async_callback = async_callback

        # We want to support multiple publishers on our topic, so we track correct
        # message ordering on a per-publisher basis.
        self._pub_counters: Dict[core.NodeID, int] = {}

        # Record any out-of-order messages for debugging and error handling
        self._unexpected_msgs: List[core.Message] = []

        # Cache of recent message latencies to calculate current avg latency
        self._latency_records: List[SubscriberLatencyRecord] = []
        self._latency_issue_count: int = 0

        self._pubsub_client = self._redis_client.pubsub()
        self._pubsub_client.subscribe(self._topic_spec.channel)

    async def listen(self) -> None:
        """Spin and asynchronously execute provided callback as messages are received.
        """

        if self._async_callback is None:
            return

        while True:
            msg = await self.get_msg()
            if msg is not None:
                await self._async_callback(msg)

    async def get_msg(self, timeout: float = float("inf")) -> Optional[core.Message]:
        """Synchronously return the next message received. By default, block forever
        waiting for the next message.
        """

        msg = None
        start_ts = time.time()
        while time.time() - start_ts < timeout:
            # redis-py has some confusing behavior with pubsub "meta" messages
            # (subscribe, unsubscribe, etc.). Upshot is that we can't simply ignore them
            # easily, so we have to read and filter them out explicitly.
            # https://github.com/andymccurdy/redis-py/issues/733
            raw_msg = self._pubsub_client.get_message()
            if raw_msg and raw_msg["type"] == "message":
                msg = self._topic_spec.msg_cls.parse_raw(raw_msg["data"])
                break
            await asyncio.sleep(REDIS_SUB_SLEEP)

        if msg is not None:
            self._check_latency(msg)
            self._check_msg_ordering(msg)

        return msg

    def _check_latency(self, msg: core.Message) -> None:
        """Check whether subscriber is experiencing any latency issues, and log if so.
        """

        window_ready = self._update_latency_records(msg)
        if not window_ready:
            return

        last_msg_latency = self._latency_records[-1].msg_latency
        if last_msg_latency > self._topic_spec.max_single_latency:
            LOGGER.warning(f"Very late message: {last_msg_latency=} {msg=}")
            self._latency_issue_count += 1

        avg_latency = np.mean([lr.msg_latency for lr in self._latency_records])
        if avg_latency > self._topic_spec.max_avg_latency:
            LOGGER.warning(
                f"Average latency exceeded: {avg_latency=} {self._latency_records=}"
            )
            self._latency_issue_count += 1

            # Reset to avoid repetitively penalizing the slow messages received during
            # this window
            self._latency_records = []

    def _update_latency_records(self, msg: core.Message) -> bool:
        """Update our cache of recent latency records. In order to avoid spurious
        latency errors at the beginning of a pubsub session, latency checks must only be
        done once we have enough data.

        Returns:
            Whether the cache of latency records is long enough to cover the required
            window of time.
        """

        # Sanity checks to make mypy happy
        if msg.pub_dt is None:
            LOGGER.warning(f"Malformed message: {msg=}")
            return False

        now_dt = datetime.now().astimezone()
        now_ts = now_dt.timestamp()

        new_latency_record = SubscriberLatencyRecord(
            msg_rcv_ts=now_ts, msg_latency=(now_dt - msg.pub_dt).total_seconds(),
        )
        self._latency_records.append(new_latency_record)

        # Filter the cache to only include messages in the current window.
        new_start_ix = 0
        for ix, lr in enumerate(self._latency_records):
            if lr.msg_rcv_ts > now_ts - LATENCY_WINDOW_S:
                # To ensure sufficient data and avoid spurious checks, we select the
                # start message to be slightly *older* than the beginning of the window.
                new_start_ix = max(0, ix - 1)
                break
        self._latency_records = self._latency_records[new_start_ix:]

        window_duration = now_ts - self._latency_records[0].msg_rcv_ts
        return window_duration >= LATENCY_WINDOW_S

    def _check_msg_ordering(self, msg: core.Message) -> None:
        """We track message ordering on a per-publisher basis, since multiple publishers
        may be sending messages to this subscriber. We expect all messages to be
        received in order.
        """

        # Sanity checks to make mypy happy
        if msg.sender_id is None or msg.pub_counter is None:
            LOGGER.warning(f"Malformed message: {msg=}")
            return

        if msg.sender_id not in self._pub_counters:
            self._pub_counters[msg.sender_id] = msg.pub_counter
        else:
            self._pub_counters[msg.sender_id] += 1
            if self._pub_counters[msg.sender_id] != msg.pub_counter:
                LOGGER.warning(f"Out-of-order message: {msg=}, {self._pub_counters=}")
                self._unexpected_msgs.append(msg)

                # Reset to avoid repetitively penalizing a dropped message and realign
                # counters
                self._pub_counters[msg.sender_id] = msg.pub_counter

    def get_latency_issue_count(self) -> int:
        return self._latency_issue_count

    def get_unexpected_msgs(self) -> List[core.Message]:
        return copy.copy(self._unexpected_msgs)

    def close(self) -> None:
        self._pub_counters = {}
        self._pubsub_client.close()
