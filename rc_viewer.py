import asyncio
import sys
import os
import time

import numpy as np  # type: ignore[import]
from ipc import core, messages, pubsub, registry
from node import base_node

# Min and max positions we can show the robot in
MAP_X_BOUNDS = (-10, 10)
MAP_Y_BOUNDS = (-10, 10)


class PotreroView(base_node.BaseNode):
    def __init__(self) -> None:
        super().__init__(registry.NodeIDs.POTRERO_VIEW)
        self._viz_welcome()
        self.add_subscribers({registry.TopicSpecs.ODOMETRY: self.rcv_odometry})

    @staticmethod
    def _viz_welcome() -> None:
        print("# Welcome to the next-gen Built Robotics UI.")
        print("# Here is a 1D map of your robot in the world.")

    async def rcv_odometry(self, msg: messages.Odometry) -> None:
        self._viz_map(msg.x_position, msg.y_position, msg.heading)

    @staticmethod
    def _viz_map(x_position: float, y_position: float, heading: str) -> None:
        x_number_line_len = int(MAP_X_BOUNDS[1] - MAP_X_BOUNDS[0])
        y_number_line_len = int(MAP_Y_BOUNDS[1] - MAP_Y_BOUNDS[0])
        
        horizontal_position = int(np.clip(x_position - MAP_X_BOUNDS[0], 0, x_number_line_len))
        vertical_position = int(np.clip(y_position - MAP_Y_BOUNDS[0], 0, y_number_line_len))

        leading_dashes = "-" * min(horizontal_position, x_number_line_len - 1)
        lagging_dashes = "-" * (x_number_line_len - horizontal_position - 1)
        lines_above_robot = min(vertical_position, y_number_line_len - 1)
        lines_below_robot = y_number_line_len - vertical_position - 1

        line_str = f"{leading_dashes}{heading}{lagging_dashes}"
        labeled_line_str = f"{MAP_X_BOUNDS[0]}|{line_str}|{MAP_X_BOUNDS[1]}"
        empty_line_str = "-" * (x_number_line_len)
        labeled_empty_str = f"{MAP_X_BOUNDS[0]}|{empty_line_str}|{MAP_X_BOUNDS[1]}"

        print(f"{MAP_Y_BOUNDS[1]} [{y_position}]")
        for i in range(lines_below_robot):
            print(f"{labeled_empty_str}")
        print(f"{labeled_line_str} [{x_position}]")
        for i in range(lines_above_robot):
            print(f"{labeled_empty_str}")
        print(f"{MAP_Y_BOUNDS[0]} [{y_position}]")


if __name__ == "__main__":
    node = PotreroView()
    node.run()
