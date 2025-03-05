from datetime import datetime

from sqlalchemy import DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db.database import Base
from ..enums.range_states import RangeState
from .template_base_model import OwnableObjectMixin


class RangeModel(Base, OwnableObjectMixin):
    """Range model class."""

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    readme: Mapped[str] = mapped_column(String, nullable=True)
    state_file: Mapped[str] = mapped_column(String, nullable=False)
    state: Mapped[RangeState] = mapped_column(Enum(RangeState), nullable=False)

    # hosts: list[CdktfBaseHost]
    # subets: list[CdktfBaseSubnet]
    # vpcs: list[CdktfBaseVPC]


# deployed_range_obj = DeployedRange(deployed_range_id, range_template, state_file, range_template.provider, account: OpenLabsAccount, cloud_account_id: uuid/int)
# OpenLabsAccount --> Provider --> Cloud Account ID --> AWS Creds
