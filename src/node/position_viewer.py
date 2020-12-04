import asyncio
import sys

import numpy as np
from ipc import core, messages, pubsub, registry
from node import base_node

# Min and max positions we can show the robot in
MAP_BOUNDS = (-10, 10)


class PotreroView(base_node.BaseNode):
    def __init__(self):
        super().__init__(registry.NodeIDs.POTRERO_VIEW)
        self._viz_welcome()
        self.add_subscribers({registry.TopicSpecs.ODOMETRY: self.rcv_odometry})

    @staticmethod
    def _viz_welcome():
        print("# Welcome to Potrero, the next-gen Built Robotics UI.")
        print("# Here is a 1D map of your robot in the world.")

    async def rcv_odometry(self, msg: messages.Odometry):
        self._viz_map(msg.position)

    @staticmethod
    def _viz_map(position):
        number_line_len = int(MAP_BOUNDS[1] - MAP_BOUNDS[0])
        line_position = int(np.clip(position - MAP_BOUNDS[0], 0, number_line_len))

        leading_dashes = "-" * min(line_position, number_line_len - 1)
        lagging_dashes = "-" * (number_line_len - line_position - 1)
        line_str = f"{leading_dashes}X{lagging_dashes}"
        labeled_line_str = f"{MAP_BOUNDS[0]}|{line_str}|{MAP_BOUNDS[1]}"

        # Add spaces at the end to overwrite old chars
        print(f"\r{labeled_line_str} [{position}]            ", end="")


if __name__ == "__main__":
    node = PotreroView()
    node.run()
