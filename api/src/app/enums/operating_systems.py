from enum import Enum


class OpenLabsOS(Enum):
    """OpenLabs supported OS."""

    DEBIAN_11 = "debian_11"  # Debian 11
    DEBIAN_12 = "debian_12"  # Debian 12
    UBUNTU_20 = "ubuntu_20"  # Debian 20.04
    UBUNTU_22 = "ubuntu_22"  # Ubuntu 22.04
    UBUNTU_24 = "ubuntu_24"  # Ubuntu 24.04
    SUSE_12 = "suse_12"  # SUSE 12
    SUSE_15 = "suse_15"  # SUSE 15
    # CENTOS_9       = "centos_9"     # CentOS Stream 9
    # CENTOS_10      = "centos_10"    # CentOS Stream 10
    KALI = "kali"  # Kali Linux
    WINDOWS_2016 = "windows_2016"  # Windows Server 2016
    WINDOWS_2019 = "windows_2019"  # Windows Server 2019
    WINDOWS_2022 = "windows_2022"  # Windows Server 2022


# Using AWS ami
AWS_OS_MAP = {
    # Debian - https://wiki.debian.org/Cloud/AmazonEC2Image
    OpenLabsOS.DEBIAN_11: "ami-053413bdacb39d8dc",
    OpenLabsOS.DEBIAN_12: "ami-0e8087266e36fe754",
    # Ubuntu - https://cloud-images.ubuntu.com/locator/ec2/
    OpenLabsOS.UBUNTU_20: "ami-014f7ab33242ea43c",
    OpenLabsOS.UBUNTU_22: "ami-0e1bed4f06a3b463d",
    OpenLabsOS.UBUNTU_24: "ami-04b4f1a9cf54c11d0",
    # SUSE
    OpenLabsOS.SUSE_12: "ami-0d6a3fb3bfdd87b52",
    OpenLabsOS.SUSE_15: "ami-0d9f9dbae7b9a241d",
    # CentOS - https://www.centos.org/download/aws-images/
    # OpenLabsOS.CENTOS_9     : "ami-0705f7887207411ca"
    # OpenLabsOS.CENTOS_10    : "ami-03753625d82454d04"
    # Kali - https://aws.amazon.com/marketplace/server/configuration?productId=804fcc46-63fc-4eb6-85a1-50e66d6c7215
    OpenLabsOS.KALI: "ami-02be3d7604aff56a7",
    # Windows
    OpenLabsOS.WINDOWS_2016: "ami-032ec7a32b7fb247c",
    OpenLabsOS.WINDOWS_2019: "ami-049dd04cca2dc5594",
    OpenLabsOS.WINDOWS_2022: "ami-0a0ebee827a585d06",
}


# URN formatted as <publisher>:<offer>:<sku>:<version>
AZURE_OS_MAP = {
    # Debian - https://wiki.debian.org/Cloud/MicrosoftAzure
    OpenLabsOS.DEBIAN_11: "Debian:debian-11:11-backports-gen2:latest",
    OpenLabsOS.DEBIAN_12: "Debian:debian-12:12-gen2:latest",
    # Ubuntu - https://documentation.ubuntu.com/azure/en/latest/azure-how-to/instances/find-ubuntu-images/
    OpenLabsOS.UBUNTU_20: "Canonical:0001-com-ubuntu-server-focal:20_04-lts-gen2:latest",
    OpenLabsOS.UBUNTU_22: "Canonical:0001-com-ubuntu-server-jammy:22_04-lts-gen2:latest",
    OpenLabsOS.UBUNTU_24: "Canonical:ubuntu-24_04-lts:server:latest",
    # SUSE
    OpenLabsOS.SUSE_12: "SUSE:sles-12-sp5:gen2:latest",
    OpenLabsOS.SUSE_15: "SUSE:sles-15-sp5:gen2:latest",
    # CentOS
    # OpenLabsOS.CENTOS_9     : ""
    # OpenLabsOS.CENTOS_10    : ""
    # Kali
    OpenLabsOS.KALI: "kali-linux:kali:kali-2024-4:2024.4.1",
    # Windows
    OpenLabsOS.WINDOWS_2016: "MicrosoftWindowsServer:WindowsServer:2016-datacenter-gensecond:latest",
    OpenLabsOS.WINDOWS_2019: "MicrosoftWindowsServer:WindowsServer:2019-datacenter-gensecond:latest",
    OpenLabsOS.WINDOWS_2022: "MicrosoftWindowsServer:WindowsServer:2022-datacenter-g2:latest",
}

# Minimum size allowed for host given an OS
OS_SIZE_THRESHOLD = {
    OpenLabsOS.DEBIAN_11: 8,
    OpenLabsOS.DEBIAN_12: 8,
    OpenLabsOS.UBUNTU_20: 8,
    OpenLabsOS.UBUNTU_22: 8,
    OpenLabsOS.UBUNTU_24: 8,
    OpenLabsOS.SUSE_12: 8,
    OpenLabsOS.SUSE_15: 8,
    OpenLabsOS.KALI: 32,
    OpenLabsOS.WINDOWS_2016: 32,
    OpenLabsOS.WINDOWS_2019: 32,
    OpenLabsOS.WINDOWS_2022: 32,
}

# SSH username mapping for each OS by provider
AWS_SSH_USERNAME_MAP = {
    OpenLabsOS.DEBIAN_11: "admin",
    OpenLabsOS.DEBIAN_12: "admin",
    OpenLabsOS.UBUNTU_20: "ubuntu",
    OpenLabsOS.UBUNTU_22: "ubuntu",
    OpenLabsOS.UBUNTU_24: "ubuntu",
    OpenLabsOS.SUSE_12: "ec2-user",
    OpenLabsOS.SUSE_15: "ec2-user",
    OpenLabsOS.KALI: "kali",
    OpenLabsOS.WINDOWS_2016: "Administrator",
    OpenLabsOS.WINDOWS_2019: "Administrator",
    OpenLabsOS.WINDOWS_2022: "Administrator",
}

AZURE_SSH_USERNAME_MAP = {
    OpenLabsOS.DEBIAN_11: "azureuser",
    OpenLabsOS.DEBIAN_12: "azureuser",
    OpenLabsOS.UBUNTU_20: "azureuser",
    OpenLabsOS.UBUNTU_22: "azureuser",
    OpenLabsOS.UBUNTU_24: "azureuser",
    OpenLabsOS.SUSE_12: "azureuser",
    OpenLabsOS.SUSE_15: "azureuser",
    OpenLabsOS.KALI: "azureuser",
    OpenLabsOS.WINDOWS_2016: "azureuser",
    OpenLabsOS.WINDOWS_2019: "azureuser",
    OpenLabsOS.WINDOWS_2022: "azureuser",
}
