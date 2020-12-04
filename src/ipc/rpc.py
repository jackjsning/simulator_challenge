"""Remote procedure call (RPC) implementation, based on top of pubsub.

RPC clients and servers should be instantiated directly in business logic.
"""

import asyncio
import logging
import os
import sys
import time
import traceback
from typing import Callable, Optional

import redis
from ipc import core, pubsub, registry

LOGGER = logging.getLogger()


# Redis settings
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_HEALTH_INTERVAL = float(os.environ.get("REDIS_HEALTH_INTERVAL", "30"))  # seconds
REDIS_GET_INTERVAL = float(os.environ.get("REDIS_GET_INTERVAL", "0.001"))  # seconds


class RPCError(Exception):
    """Base exception for this module."""

    pass


class DuplicateServerError(RPCError):
    """Raised if another server is already handling this RPC call."""

    pass


class RPCServerCall:
    """Transient object that represents a currently executing procedure.

    Instantiated on the server side to contain the execution state.

    Attributes:
        request_msg: the request that initiated this execution of the procedure
        _async_proc_func: coroutine function that implements procedure's business logic
        _task: task for the running procedure
    """

    def __init__(
        self, request_msg: core.RPCRequest, async_proc_func: Callable,
    ):
        self.request_msg = request_msg
        self._async_proc_func = async_proc_func
        self._task: Optional[asyncio.Task] = None

    async def execute(self) -> core.RPCResponse:
        """Run the given procedure function.

        Returns:
            RPC response with fields filled in appropriately
        """

        self._task = asyncio.create_task(self._async_proc_func(self.request_msg))
        response = core.RPCResponse(request_msg=self.request_msg)
        start_ts = time.time()

        # Use try/except to ensure that we return a response, even if the procedure
        # function errors.
        try:
            response.return_val = await self._task
        except asyncio.exceptions.CancelledError:
            response.cancelled = True
        except:
            response.traceback_str = traceback.format_exc()

        response.duration = time.time() - start_ts
        return response

    def cancel(self) -> None:
        if self._task is not None:
            self._task.cancel()


class BaseRPCAgent:
    """Simple common logic for clients and servers."""

    def __init__(
        self, node_id: core.NodeID, rpc_spec: core.RPCSpec,
    ):
        self._node_id = node_id
        self._rpc_spec = rpc_spec
        self._redis_client = redis.Redis(
            host=REDIS_HOST,
            port=self._rpc_spec.broker_spec.port,
            health_check_interval=REDIS_HEALTH_INTERVAL,
        )  # type: ignore[call-arg]  # Redis types sometimes are out of date
        self._cur_request_msg = None

    @property
    def _request_topic_spec(self) -> core.TopicSpec:
        return self._rpc_spec.request_topic_spec

    def _get_response_topic_spec(self, sender_id: core.NodeID) -> core.TopicSpec:
        return self._rpc_spec.get_response_topic_spec(sender_id)

    @property
    def _cancel_topic_spec(self) -> core.TopicSpec:
        return self._rpc_spec.cancel_topic_spec


class RPCServer(BaseRPCAgent):
    """Server implementation, should be instatiated in business logic.

    Enables receiving RPC requests and running procedures in response. Procedures may
    optionally pass back a return value, as well.
    """

    def __init__(
        self, node_id: core.NodeID, rpc_spec: core.RPCSpec, async_proc_func: Callable,
    ):
        super().__init__(node_id, rpc_spec)

        # Not easy to type hint a coroutine function (as opposed to a coroutine), so we
        # check it dynamically
        if not asyncio.iscoroutinefunction(async_proc_func):
            raise TypeError("Expecting coroutine function")
        self._async_proc_func = async_proc_func

        self._cur_rpc_call: Optional[RPCServerCall] = None
        self._update_status()

        self._request_sub = pubsub.Subscriber(
            self._node_id, self._request_topic_spec, self._handle_request,
        )
        self._cancel_sub = pubsub.Subscriber(
            self._node_id, self._cancel_topic_spec, self._handle_cancel,
        )

    def _update_status(self) -> None:
        # Ensure no duplicate servers are already running for this RPC. Note that this
        # is *NOT* thread-safe, since another server could come up while this method is
        # running, but in practice we don't expect server launches to be frequent.
        raw_status = self._redis_client.get(self._rpc_spec.status_key)
        if raw_status is not None:
            cur_status = core.RPCStatus.parse_raw(raw_status)
            if cur_status.server_id != self._node_id:
                raise DuplicateServerError

        cur_request = None if not self._cur_rpc_call else self._cur_rpc_call.request_msg
        new_status = core.RPCStatus(server_id=self._node_id, cur_request=cur_request)
        self._redis_client.set(self._rpc_spec.status_key, new_status.json())

    async def _handle_request(self, request_msg: core.RPCRequest) -> None:
        # Not easy to type hint request (dynamic type), so we check it dynamically
        if not isinstance(request_msg, self._request_topic_spec.msg_cls):
            raise TypeError(f"{request_msg=} {self._request_topic_spec.msg_cls=}")

        self._cur_rpc_call = RPCServerCall(request_msg, self._async_proc_func)
        self._update_status()

        rpc_response = await self._cur_rpc_call.execute()
        self._publish_response(rpc_response)

        self._cur_rpc_call = None
        self._update_status()

    def _publish_response(self, rpc_response: core.RPCResponse) -> None:
        # Sanity checks for mypy
        if (
            rpc_response.request_msg is None
            or rpc_response.request_msg.sender_id is None
        ):
            LOGGER.warning(f"Malformed RPC response: {rpc_response=}")
            return

        # Publishers are lightweight, so we create a disposable one for this particular
        # response
        response_pub = pubsub.Publisher(
            self._node_id,
            self._get_response_topic_spec(rpc_response.request_msg.sender_id),
        )
        response_pub.publish(rpc_response)

    async def _handle_cancel(self, cancel_msg: core.RPCCancel) -> None:
        if self._cur_rpc_call is not None:
            self._cur_rpc_call.cancel()

    async def serve(self) -> None:
        """Spin and appropriately handle received requests and cancellations."""

        await asyncio.gather(self._request_sub.listen(), self._cancel_sub.listen())

    def close(self) -> None:
        self._redis_client.delete(self._rpc_spec.status_key)
        self._request_sub.close()
        self._cancel_sub.close()


class RPCClient(BaseRPCAgent):
    """Client implementation, should be instatiated in business logic.

    Enables making RPC requests (aka procedure calls) and waiting for the corresponding
    response. Can be done synchronously or, via an asyncio Task, asynchronously.
    """

    def __init__(self, node_id: core.NodeID, rpc_spec: core.RPCSpec):
        super().__init__(node_id, rpc_spec)
        self._request_pub = pubsub.Publisher(self._node_id, self._request_topic_spec)
        self._cancel_pub = pubsub.Publisher(self._node_id, self._cancel_topic_spec)
        self._response_sub = pubsub.Subscriber(
            self._node_id, self._get_response_topic_spec(self._node_id), None,
        )

    async def call(self, request_msg: core.RPCRequest) -> core.RPCResponse:
        """Sends the provided RPC request to the RPC server.

        Returns:
            The RPC response associated with this request, which may itself have a
            return value field set with any necessary business data from the procedure
            function.
        """

        self._request_pub.publish(request_msg)
        response_msg = await self._response_sub.get_msg()
        if not isinstance(response_msg, core.RPCResponse):
            raise TypeError(f"{response_msg=}")
        return response_msg

    def cancel_running_procedure(self) -> None:
        """Cancel the server's currently running procedure, if any.

        Note that procedure may have been initiated by a different client. Also, there
        may be another request in the queue, so the server may become busy immediately
        again after this cancellation goes through.
        """

        self._cancel_pub.publish(core.RPCCancel())

    def get_status(self) -> Optional[core.RPCStatus]:
        raw_status = self._redis_client.get(self._rpc_spec.status_key)
        return None if not raw_status else core.RPCStatus.parse_raw(raw_status)

    def close(self) -> None:
        self._response_sub.close()
