from enum import Enum


class OpenLabsSpec(Enum):
    """OpenLabs VM hardware specifications."""

    TINY = "tiny"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    HUGE = "huge"


# https://aws.amazon.com/ec2/instance-types/t2/
AWS_SPEC_MAP = {
    OpenLabsSpec.TINY: "t2.nano",  # 1 vCPU, 0.5 GiB RAM
    OpenLabsSpec.SMALL: "t2.small",  # 1 vCPU, 2.0 GiB RAM
    OpenLabsSpec.MEDIUM: "t2.medium",  # 2 vCPU, 4.0 GiB RAM
    OpenLabsSpec.LARGE: "t2.large",  # 2 vCPU, 8.0 GiB RAM
    OpenLabsSpec.HUGE: "t2.xlarge",  # 4 vCPU, 16.0 GiB RAM
}


# https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/general-purpose/bv1-series?tabs=sizebasic
AZURE_SPEC_MAP = {
    OpenLabsSpec.TINY: "Standard_B1ls",   # 1 vCPU, 0.5 GiB RAM
    OpenLabsSpec.SMALL: "Standard_B1ms",  # 1 vCPU, 2.0 GiB RAM
    OpenLabsSpec.MEDIUM: "Standard_B2s",  # 2 vCPU, 4.0 GiB RAM
    OpenLabsSpec.LARGE: "Standard_B2ms",  # 2 vCPU, 8.0 GiB RAM
    OpenLabsSpec.HUGE: "Standard_B4ms",   # 4 vCPU, 16.0 GiB RAM
}
