import asyncio
import sys

import numpy as np  # type: ignore[import]
from ipc import core, messages, pubsub, registry
from node import base_node
import enum

# Min and max positions the robot can be in
WORLD_X_EDGES = (-10, 10)
WORLD_Y_EDGES = (-10, 10)

class Heading(enum.Enum):
    EAST = enum.auto()
    WEST = enum.auto()
    NORTH = enum.auto()
    SOUTH = enum.auto()

class Simulator(base_node.BaseNode):
    def __init__(self) -> None:
        self._direction = None
        super().__init__(registry.NodeIDs.SIMULATOR)
        self._x_position = 0
        self._y_position = 0
        self._heading = Heading.NORTH

        self.add_publishers(registry.TopicSpecs.ODOMETRY)
        #self.add_subscribers({registry.TopicSpecs.RC_JS_DEF: self.rcv_js})
        self.add_subscribers({registry.TopicSpecs.USER_INPUT: self.user_in})
        self.add_tasks(self._pub_odometry_loop)
    
    def get_heading_str(self):
        if self._heading == Heading.EAST:
            return '>'
        elif self._heading == Heading.WEST:
            return '<'
        elif self._heading == Heading.SOUTH:
            return 'v'
        elif self._heading == Heading.NORTH:
            return '^'

    def rotate_right(self):
        if self._heading == Heading.EAST:
            self._heading = Heading.SOUTH
        elif self._heading == Heading.SOUTH:
            self._heading = Heading.WEST
        elif self._heading == Heading.WEST:
            self._heading = Heading.NORTH
        elif self._heading == Heading.NORTH:
            self._heading = Heading.EAST

    def rotate_left(self):
        if self._heading == Heading.EAST:
            self._heading = Heading.NORTH
        elif self._heading == Heading.SOUTH:
            self._heading = Heading.EAST
        elif self._heading == Heading.WEST:
            self._heading = Heading.SOUTH
        elif self._heading == Heading.NORTH:
            self._heading = Heading.WEST

    def move_forward(self):
        if self._heading == Heading.EAST:
            self._x_position += .5
        elif self._heading == Heading.SOUTH:
            self._y_position -= .5
        elif self._heading == Heading.WEST:
            self._x_position -= .5
        elif self._heading == Heading.NORTH:
            self._y_position += .5

    def move_backwards(self):
        if self._heading == Heading.EAST:
            self._x_position -= .5
        elif self._heading == Heading.SOUTH:
            self._y_position += .5
        elif self._heading == Heading.WEST:
            self._x_position += .5
        elif self._heading == Heading.NORTH:
            self._y_position -= .5

    def move_robot(self):
        if self._direction == messages.Direction.LEFT:
            self.rotate_left()
        elif self._direction == messages.Direction.RIGHT:
            self.rotate_right()
        elif self._direction == messages.Direction.FORWARD:
            self.move_forward()
        elif self._direction == messages.Direction.BACKWARD:
            self.move_backwards()

    async def rcv_js(self, msg: messages.JoystickDeflection) -> None:
        self._position = np.clip(self._position + msg.deflection, *WORLD_X_EDGES)

    async def user_in(self, msg: messages.Direction) -> None:
        self._direction  = msg.direction
        self.move_robot()
        self._x_position = np.clip(self._x_position, *WORLD_X_EDGES)
        self._y_position = np.clip(self._y_position, *WORLD_Y_EDGES)

    async def _pub_odometry_loop(self) -> None:
        while True:
            msg = messages.Odometry(x_position=self._x_position, y_position = self._y_position, heading = self.get_heading_str())
            self.publish(registry.TopicSpecs.ODOMETRY, msg)
            await asyncio.sleep(0.05)


if __name__ == "__main__":
    node = Simulator()
    node.run()
