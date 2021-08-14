"""Business-logic implementations for specific IPC messages, including RPC requests.
"""

import enum
import sys

import pydantic
from ipc import core

########################################################################################
# DEBUG ################################################################################
########################################################################################


class Debug(core.Message):
    content: str


class DebugRequest(core.RPCRequest):
    content: str


########################################################################################
# RAW HW MSGS ##########################################################################
########################################################################################


class JoystickType(enum.Enum):
    # Track joysticks
    TRACK_LEFT = "track_left"
    TRACK_RIGHT = "track_right"

    # Left joystick
    CAB_SWING = "cab_swing"
    STICK = "stick"

    # Right joystick
    BUCKET = "bucket"
    BOOM = "boom"


class JoystickDeflection(core.Message):
    joystick: JoystickType
    deflection: pydantic.confloat(ge=-1.0, le=1.0)  # type: ignore[valid-type]

class Direction(enum.Enum):
    # Robot movement
    LEFT = "left"
    RIGHT = "right"
    FORWARD = "forward"
    BACKWARD = "backward"

class UserInput(core.Message):
    direction: Direction

########################################################################################
# PROCESSED SENSOR DATA ################################################################
########################################################################################


class Odometry(core.Message):
    # TODO: Fill this out, of course
    x_position: float
    y_position: float
    heading: str


########################################################################################
# RPC ##################################################################################
########################################################################################


class NavigateRequest(core.RPCRequest):
    # TODO: Fill this out, of course
    position: float
    tolerance: float = 0.1
