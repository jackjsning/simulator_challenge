import asyncio
import sys
import termios
import time
import tty
from typing import Optional

from ipc import core, messages, pubsub, registry
from node import base_node


class PotreroRC(base_node.BaseNode):
    def __init__(self) -> None:
        super().__init__(registry.NodeIDs.POTRERO_RC)
        self.add_publishers(registry.TopicSpecs.USER_INPUT)
        self.add_tasks(self._read_keyboard, self._viz_pub_loop)

        self._direction: Optional[messages.Direction] = None
        self._viz_welcome()

    @staticmethod
    def _viz_welcome() -> None:
        print("# Welcome to Potrero, the next-gen Built Robotics UI.")
        print("# Use the left and right arrow keys to turn your robot")
        print("# Use the up and down arrow keys to move your robot forward and backwards")
        print("#'q' to exit.")

    @staticmethod
    def _extract_direction(arrow_key_bytes: str) -> Optional[str]:
        """Returns the direction of the arrow key pressed."""
        if arrow_key_bytes == "[D":
            direction: Optional[messages.Direction] = messages.Direction.LEFT
        elif arrow_key_bytes == "[C":
            direction = messages.Direction.RIGHT
        elif arrow_key_bytes == "[A":
            direction = messages.Direction.FORWARD
        elif arrow_key_bytes == "[B":
            direction = messages.Direction.BACKWARD
        else:
            direction = None
        return direction

    def _read_keyboard(self) -> None:
        # Change terminal settings so that we can receive keypresses for arrow keys without waiting
        # for a newline.
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)

        while True:
            try:
                tty.setraw(fd)
                ch = sys.stdin.read(1)

                # Arrow keys are read as 3-byte sequences. This looks for the sentinel character at
                # the beginning, then reads the next 2 bytes.
                if ch == "\x1b":
                    arrow_key_bytes = sys.stdin.read(2)
                    self._direction = self._extract_direction(arrow_key_bytes)
                if ch == "q":
                    print("\r\n", end="")
                    self.stop()
                    break
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    async def _viz_pub_loop(self) -> None:
        while True:
            dir_label = " " if self._direction is None else self._direction
            print(f"\rDIRECTION: [{dir_label}]", end="")

            #Add rotation
            if self._direction is not None:
                #js_def = -0.5 if self._direction == "L" else 0.5
                msg = messages.UserInput(
                    direction = self._direction
                )
                self.publish(registry.TopicSpecs.USER_INPUT, msg)
            self._direction = None

            await asyncio.sleep(0.1)


if __name__ == "__main__":
    node = PotreroRC()
    node.run()
