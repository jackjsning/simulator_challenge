"""Listings for all commonly recognized IPC components. Should be updated frequently as
business logic is built out.

Enables coordination of communication between different parts of the system (e.g.,
ensures both publishers and subscribers using the same topic spec).
"""

import sys
import typing
from typing import Any, List, Tuple

import pydantic
from ipc import core, messages


class RegistryInstantionError(Exception):
    pass


class Registry:
    """Base class to enable easily defining lists of recognized items (constants) such
    that auto-complete and static code checks are supported.

    Similar to an enum, but with a bit less magic.

    Not to be instantiated. Instead just use the class object directly.
    """

    def __init__(self) -> None:
        raise RegistryInstantionError

    @classmethod
    def items(cls) -> List[Tuple[str, Any]]:
        public_attr_names = [k for k in cls.__dict__.keys() if not k.startswith("_")]
        return [(name, getattr(cls, name)) for name in public_attr_names]


class BrokerSpecs(Registry):
    """Note that our system expects and requires Redis instances to be running as
    defined here.
    """

    GENERAL = core.BrokerSpec(name="general", port=6379)


class NodeIDs(Registry):
    SIMULATOR = core.NodeID(name="simulator")
    NAVIGATE_SERVER = core.NodeID(name="navigate_server")

    POTRERO_RC = core.NodeID(name="potrero_rc")
    POTRERO_VIEW = core.NodeID(name="potrero_view")

    DEBUG0 = core.NodeID(name="debug0")
    DEBUG1 = core.NodeID(name="debug1")


class TopicSpecs(Registry):
    RC_JS_DEF = core.TopicSpec(
        broker_spec=BrokerSpecs.GENERAL,
        channel="rc_js_def",
        msg_cls=messages.JoystickDeflection,
    )
    AUTO_JS_DEF = core.TopicSpec(
        broker_spec=BrokerSpecs.GENERAL,
        channel="auto_js_def",
        msg_cls=messages.JoystickDeflection,
    )
    ODOMETRY = core.TopicSpec(
        broker_spec=BrokerSpecs.GENERAL,
        channel="odometry",
        msg_cls=messages.Odometry,
    )

    DEBUG = core.TopicSpec(
        broker_spec=BrokerSpecs.GENERAL,
        channel="debug",
        msg_cls=messages.Debug,
    )


class RPCSpecs(Registry):
    DEBUG = core.RPCSpec(BrokerSpecs.GENERAL, "debug", messages.DebugRequest)
    NAVIGATE = core.RPCSpec(BrokerSpecs.GENERAL, "navigate", messages.NavigateRequest)
