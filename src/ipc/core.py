"""Primary data types that our IPC system depends on.

Most classes can be instantiated directly, though some should generally be extended by
implementing code (see messages.py).
"""

import sys
from datetime import datetime
from typing import Any, Optional, Type

import pydantic


class BrokerSpec(pydantic.BaseModel):
    """Specification for which pubsub broker to connect to. Used for defining topic
    and RPC specs. We implement brokers as Redis instances.
    """

    name: str
    port: int
    # TODO: Unused for now, but probably needed for eventual Redis config
    hostname: Optional[str] = None


class NodeID(pydantic.BaseModel):
    """Typed identifier for node names (clearer than just using plain strs)."""

    name: str

    def __hash__(self) -> int:
        return hash(self.name)


class Message(pydantic.BaseModel):
    """Base class for all IPC messages. Generally should be subclassed with additional
    fields as needed. Publisher business logic should fill in additional fields, with
    the Publisher implementation filling in basic data.
    """

    # Set on publish
    sender_id: Optional[NodeID] = None  # Node that sent the message
    pub_dt: Optional[datetime] = None  # Time-zone aware time msg was published
    pub_counter: Optional[int] = None  # Enables message ordering check


class RPCRequest(Message):
    """Base class for all RPC requests. Generally should be subclassed. Though the
    current implementation doesn't include any functionality, it still enables clearer
    type checking.
    """

    pass


class RPCResponse(Message):
    """Class for RPC responses. Should *not* be subclassed -- if a return value for a
    procedure function is needed, we should use the provided field.

    This class is not subclassed because RPC servers must handle the case where the
    procedure function errors, and therefore cannot rely on receiving a procedure-
    specific response class when the function completes and returns. Instead, the
    RPC response must be generic, and treat the procedure return value (if any) as a
    payload.
    """

    # Set on publish
    request_msg: Optional[RPCRequest] = None  # Request that initiated response
    duration: Optional[float] = None  # seconds
    return_val: Optional[Any]  # Return value for the RPC procedure func
    cancelled: Optional[bool] = None  # Whether this call was cancelled
    traceback_str: Optional[str] = None  # Only set if procedure function errors

    @property
    def errored(self) -> bool:
        return self.traceback_str is not None

    @property
    def completed(self) -> bool:
        return not self.cancelled and not self.errored


class RPCCancel(Message):
    """Cancels the procedure call the server is currently executing (if any).

    Cancel messages do not specify a particular RPC call ID, so any RPC client may
    cancel any running procedure.

    In addition, RPC requests may be queued up waiting to be processed, so canceling a
    given procedure may not free up the server -- it may just move on to the next
    request in the queue.
    """

    pass


class RPCStatus(pydantic.BaseModel):
    """Status that RPC server shares in Redis key/value store. Allows monitoring the
    server to see if it is ready or busy.
    """

    server_id: NodeID  # ID of node serving thes RPC calls
    cur_request: Optional[RPCRequest] = None  # Request being processed, if any

    @property
    def ready(self) -> bool:
        return self.cur_request is None


class TopicSpec(pydantic.BaseModel):
    """Specification for a pubsub topic. Should provide everything a publisher or
    subscriber needs to know to start using the topic.
    """

    broker_spec: BrokerSpec
    channel: str  # Redis channel that pubsub will use
    msg_cls: Type[Message]  # Class that all messages will instantiate

    # These fields allow the subscriber to perform latency health checks. Default values
    # make sense for typical size messages, but should be increased for very large
    # messages like images or large numpy arrays.
    max_single_latency: float = 0.05  # All messages must be fresher than this, seconds
    max_avg_latency: float = 0.01  # Average latency must be better, seconds

    def __hash__(self) -> int:
        return hash(f"{self.broker_spec.port}{self.channel}")


class RPCSpec:
    """Specification for a remote procedure call (RPC). Should provide everything a
    client or server needs to know to make calls and respond.

    This spec just covers communication -- implementation of the RPC procedure should be
    done in business logic and passed into RPC server instances.

    RPC is inherently a request-response paradigm, meaning that each RPC will have a
    request topic and a response topic. In practice we actually have a separate response
    topic for each client/requester, to avoid clients receiving each other's responses.
    In addition, we need a cancel topic to allow clients to cancel procedures as needed.

    Attributes:
        broker_spec: which broker the underlying RPC topics should use
        base_channel: common ID slug for all the RPC's topics
        request_msg_cls: class RPC requests should instantiate (responses and cancels
            are always the same across RPCs)
    """

    _rpc_slug = "rpc-"  # Prefix all str identifiers (Redis channels and keys)

    def __init__(
        self,
        broker_spec: BrokerSpec,
        base_channel: str,
        request_msg_cls: Type[RPCRequest],
    ):
        self.broker_spec = broker_spec
        self._base_channel = base_channel
        self._request_msg_cls = request_msg_cls

    @property
    def request_topic_spec(self) -> TopicSpec:
        ch = self._rpc_slug + "request-" + self._base_channel
        return TopicSpec(
            broker_spec=self.broker_spec,
            channel=ch,
            msg_cls=self._request_msg_cls,
            max_single_latency=0.1,
            max_avg_latency=0.1,
        )

    def get_response_topic_spec(self, requester_id: NodeID) -> TopicSpec:
        """Generates the correct topic spec for responses that will be received by the
        given client node. We use different response topics for each requester so that
        they don't receive each other's responses.

        Args:
            requester_id: NodeID of the RPC requester/client
        """
        ch = self._rpc_slug + "response-" + self._base_channel + "-" + requester_id.name
        return TopicSpec(
            broker_spec=self.broker_spec,
            channel=ch,
            msg_cls=RPCResponse,
            max_single_latency=0.1,
            max_avg_latency=0.1,
        )

    @property
    def cancel_topic_spec(self) -> TopicSpec:
        ch = self._rpc_slug + "cancel-" + self._base_channel
        return TopicSpec(
            broker_spec=self.broker_spec,
            channel=ch,
            msg_cls=RPCCancel,
            max_single_latency=0.1,
            max_avg_latency=0.1,
        )

    @property
    def status_key(self) -> str:
        """Used for storing and retrieving the RPC server's status in Redis key/value
        store.
        """
        return self._rpc_slug + "status-" + self._base_channel
