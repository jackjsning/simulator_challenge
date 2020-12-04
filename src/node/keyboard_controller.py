import asyncio
import sys
import termios
import time
import tty

from ipc import core, messages, pubsub, registry
from node import base_node


class PotreroRC(base_node.BaseNode):
    def __init__(self):
        super().__init__(registry.NodeIDs.POTRERO_RC)
        self.add_publishers(registry.TopicSpecs.RC_JS_DEF)
        self.add_tasks(self._read_keyboard, self._viz_pub_loop)

        self._direction = None
        self._viz_welcome()

    @staticmethod
    def _viz_welcome():
        print("# Welcome to Potrero, the next-gen Built Robotics UI.")
        print("# Use the left and right arrow keys to RC your robot, 'q' to exit.")

    @staticmethod
    def _extract_direction(arrow_key_bytes):
        """Returns the direction of the arrow key pressed."""
        if arrow_key_bytes == "[D":
            direction = "L"
        elif arrow_key_bytes == "[C":
            direction = "R"
        else:
            direction = None
        return direction

    def _read_keyboard(self):
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

    async def _viz_pub_loop(self):
        while True:
            dir_label = " " if self._direction is None else self._direction
            print(f"\rDIRECTION: [{dir_label}]", end="")

            if self._direction is not None:
                js_def = -0.5 if self._direction == "L" else 0.5
                msg = messages.JoystickDeflection(
                    joystick=messages.JoystickType.TRACK_LEFT, deflection=js_def
                )
                self.publish(registry.TopicSpecs.RC_JS_DEF, msg)
            self._direction = None

            await asyncio.sleep(0.1)


if __name__ == "__main__":
    node = PotreroRC()
    node.run()
