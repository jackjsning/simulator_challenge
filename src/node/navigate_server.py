import asyncio
import sys
from typing import Optional

from ipc import core, messages, pubsub, registry
from node import base_node


class NavigateServer(base_node.BaseNode):
    """Navigate RPC server."""

    def __init__(self):
        super().__init__(registry.NodeIDs.NAVIGATE_SERVER)

        self._position: Optional[float] = None

        # EVENTUALLYTODO: Should be auto, not RC...
        self.add_publishers(registry.TopicSpecs.RC_JS_DEF)
        self.add_subscribers({registry.TopicSpecs.ODOMETRY: self._rcv_odom})
        self.add_rpc_servers({registry.RPCSpecs.NAVIGATE: self.navigate})

    async def _rcv_odom(self, msg: messages.Odometry):
        self._position = msg.position

    async def navigate(self, msg: messages.NavigateRequest):
        while abs(self._position - msg.position) > msg.tolerance:
            direction_sign = -1 if msg.position < self._position else 1
            js_def = direction_sign * 0.1
            self.publish(
                registry.TopicSpecs.RC_JS_DEF,
                messages.JoystickDeflection(
                    joystick=messages.JoystickType.TRACK_LEFT, deflection=js_def
                ),
            )
            await asyncio.sleep(0.05)


if __name__ == "__main__":
    node = NavigateServer()
    node.run()
