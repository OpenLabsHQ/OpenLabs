from enum import Enum


class OpenLabsProvider(str, Enum):
    """OpenLabs supported cloud providers."""

    AWS = "aws"
    AZURE = "azure"
