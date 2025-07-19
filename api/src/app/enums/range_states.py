from enum import Enum


class RangeState(Enum):
    """OpenLabs range states."""

    ON = "on"
    OFF = "off"
    STARTING = "starting"
    STOPPING = "stopping"
