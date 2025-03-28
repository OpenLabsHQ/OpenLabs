from enum import Enum


class RangeState(Enum):
    """OpenLabs range states."""

    ON = "on"
    OFF = "off"
    START = "start"
    STOP = "stop"
