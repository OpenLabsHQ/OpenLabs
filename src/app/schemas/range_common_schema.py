from pydantic import BaseModel, Field

from ..enums.providers import OpenLabsProvider


class RangeCommonSchema(BaseModel):
    """Common range attributes."""

    provider: OpenLabsProvider = Field(
        ...,
        description="Cloud provider",
        examples=[OpenLabsProvider.AWS, OpenLabsProvider.AZURE],
    )
    name: str = Field(..., min_length=1, examples=["openlabs-practice-1"])
    vnc: bool = Field(default=False, description="Automatic VNC configuration")
    vpn: bool = Field(default=False, description="Automatic VPN configuration")
