import asyncio
import sys

import numpy as np  # type: ignore[import]
from ipc import core, messages, pubsub, registry
from node import base_node

# Min and max positions the robot can be in
WORLD_EDGES = (-10, 10)


class Simulator(base_node.BaseNode):
    def __init__(self) -> None:
        super().__init__(registry.NodeIDs.SIMULATOR)
        self._position = 0

        self.add_publishers(registry.TopicSpecs.ODOMETRY)
        self.add_subscribers({registry.TopicSpecs.RC_JS_DEF: self.rcv_js})
        self.add_tasks(self._pub_odometry_loop)

    async def rcv_js(self, msg: messages.JoystickDeflection) -> None:
        self._position = np.clip(self._position + msg.deflection, *WORLD_EDGES)

    async def _pub_odometry_loop(self) -> None:
        while True:
            msg = messages.Odometry(position=self._position)
            self.publish(registry.TopicSpecs.ODOMETRY, msg)
            await asyncio.sleep(0.05)


if __name__ == "__main__":
    node = Simulator()
    node.run()
