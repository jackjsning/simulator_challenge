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


class SignalQuest(core.Message):
    roll: int  # tenth degs
    pitch: int  # tenth degs -- termed "elevation" in the SQ docs

    roll_vel: int  # tenth degs per second
    pitch_vel: int  # tenth degs per second
    yaw_vel: int  # tenth degs per second

    x_accel: int  # milligees
    y_accel: int  # milligees
    z_accel: int  # milligees

    checksum: int  # see docs


########################################################################################
# PROCESSED SENSOR DATA ################################################################
########################################################################################


class Odometry(core.Message):
    # TODO: Fill this out, of course
    position: float


########################################################################################
# RPC ##################################################################################
########################################################################################


class NavigateRequest(core.RPCRequest):
    # TODO: Fill this out, of course
    position: float
    tolerance: float = 0.1
