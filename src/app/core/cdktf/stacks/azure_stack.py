from cdktf_cdktf_provider_azurerm.nat_gateway import NatGateway
from cdktf_cdktf_provider_azurerm.nat_gateway_public_ip_association import (
    NatGatewayPublicIpAssociation,
)
from cdktf_cdktf_provider_azurerm.network_interface import NetworkInterface
from cdktf_cdktf_provider_azurerm.network_security_group import NetworkSecurityGroup
from cdktf_cdktf_provider_azurerm.network_security_rule import NetworkSecurityRule
from cdktf_cdktf_provider_azurerm.provider import AzurermProvider
from cdktf_cdktf_provider_azurerm.public_ip import PublicIp
from cdktf_cdktf_provider_azurerm.resource_group import ResourceGroup
from cdktf_cdktf_provider_azurerm.route import Route
from cdktf_cdktf_provider_azurerm.route_table import RouteTable
from cdktf_cdktf_provider_azurerm.subnet import Subnet
from cdktf_cdktf_provider_azurerm.subnet_nat_gateway_association import (
    SubnetNatGatewayAssociation,
)
from cdktf_cdktf_provider_azurerm.subnet_network_security_group_association import (
    SubnetNetworkSecurityGroupAssociation,
)
from cdktf_cdktf_provider_azurerm.subnet_route_table_association import (
    SubnetRouteTableAssociation,
)
from cdktf_cdktf_provider_azurerm.virtual_machine import (
    VirtualMachine,
)
from cdktf_cdktf_provider_azurerm.virtual_network import VirtualNetwork

from ....enums.operating_systems import AZURE_OS_MAP
from ....enums.regions import AZURE_REGION_MAP, OpenLabsRegion
from ....enums.specs import AZURE_SPEC_MAP
from ....schemas.template_range_schema import TemplateRangeSchema
from .base_stack import AbstractBaseStack


class AzureStack(AbstractBaseStack):
    """Stack for generating terraform for Azure."""

    def build_resources(
        self,
        template_range: TemplateRangeSchema,
        region: OpenLabsRegion,
        cdktf_id: str,
        range_name: str,
    ) -> None:
        """Initialize Azure terraform stack.

        Args:
        ----
            template_range (TemplateRangeSchema): Template range object to build terraform for.
            region (OpenLabsRegion): Support OpenLabs cloud region.
            cdktf_id (str): Unique ID for each deployment to use for Terraform resource naming.
            range_name (str): Name of range to deploy.

        Returns:
        -------
            None

        """
        AzurermProvider(
            self,
            "AZURE",
            features=[{}],
        )

        # Step 1: Create a Resource Group
        sanitized_name = range_name.replace(" ", "-")

        resource_group = ResourceGroup(
            self,
            f"{sanitized_name}-ResourceGroup",
            name=f"{sanitized_name}-rg",
            location=AZURE_REGION_MAP[region],
        )

        # Step 2: Create SSH Public Key resource
        # Replace with key that is generated per-range
        user_public_key = (
            template_range.ssh_key
            if hasattr(template_range, "ssh_key") and template_range.ssh_key
            else "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIH8URIMqVKb6EAK4O+E+9g8df1uvcOfpvPFl7sQrX7KM email@example.com"
        )

        for vpc in template_range.vpcs:
            # Step 3: Create a Virtual Network (equivalent to VPC in AWS)
            vnet = VirtualNetwork(
                self,
                vpc.name,
                name=vpc.name,
                resource_group_name=resource_group.name,
                location=resource_group.location,
                address_space=[str(vpc.cidr)],
            )

            # Function to derive a subnet CIDR from the VPC CIDR
            def modify_cidr(vpc_cidr: str, new_third_octet: int) -> str:
                ip_part, prefix = vpc_cidr.split("/")
                octets = ip_part.split(".")
                octets[2] = str(new_third_octet)  # Change the third octet
                octets[3] = "0"  # Explicitly set the fourth octet to 0
                return f"{'.'.join(octets)}/24"  # Convert back to CIDR

            # Generate the new subnet CIDR with third octet = 99
            public_subnet_cidr = modify_cidr(str(vpc.cidr), 99)

            # Step 4: Create a Public Subnet for the Jump Box
            public_subnet = Subnet(
                self,
                f"RangePublicSubnet-{vpc.name}",
                name=f"RangePublicSubnet-{vpc.name.replace(' ', '-')}",
                resource_group_name=resource_group.name,
                virtual_network_name=vnet.name,
                address_prefixes=[public_subnet_cidr],
            )

            # Step 5: Create Network Security Group for Jump Box
            jumpbox_nsg = NetworkSecurityGroup(
                self,
                f"RangeJumpBoxNSG-{vpc.name}",
                name=f"RangeJumpBoxNSG-{vpc.name.replace(' ', '-')}",
                resource_group_name=resource_group.name,
                location=resource_group.location,
            )

            # Step 6: Create NSG Rules for Jump Box
            NetworkSecurityRule(
                self,
                f"RangeAllowSSH-{vpc.name}",
                name="AllowSSH",
                resource_group_name=resource_group.name,
                network_security_group_name=jumpbox_nsg.name,
                priority=100,
                direction="Inbound",
                access="Allow",
                protocol="Tcp",
                source_port_range="*",
                destination_port_range="22",
                source_address_prefix="*",
                destination_address_prefix="*",
            )

            # Figure out why private subnet doesnt get outbound ICMP
            # Allow ICMP inbound
            NetworkSecurityRule(
                self,
                f"RangeAllowICMPInbound-{vpc.name}",
                name="AllowICMPInbound",
                resource_group_name=resource_group.name,
                network_security_group_name=jumpbox_nsg.name,
                priority=110,
                direction="Inbound",
                access="Allow",
                protocol="Icmp",
                source_port_range="*",
                destination_port_range="*",
                source_address_prefix="*",
                destination_address_prefix="*",
            )

            # Allow ICMP outbound
            NetworkSecurityRule(
                self,
                f"JumpboxAllowICMPOutbound-{vpc.name}",
                name="AllowICMPOutbound",
                resource_group_name=resource_group.name,
                network_security_group_name=jumpbox_nsg.name,
                priority=120,
                direction="Outbound",
                access="Allow",
                protocol="Icmp",
                source_port_range="*",
                destination_port_range="*",
                source_address_prefix="*",
                destination_address_prefix="*",
            )

            # Step 7: Associate NSG with Public Subnet
            SubnetNetworkSecurityGroupAssociation(
                self,
                f"RangePublicSubnetNSGAssociation-{vpc.name}",
                subnet_id=public_subnet.id,
                network_security_group_id=jumpbox_nsg.id,
            )

            # Step 8: Create Route Table for public subnet
            public_route_table = RouteTable(
                self,
                f"RangePublicRouteTable-{vpc.name}",
                name=f"RangePublicRouteTable-{vpc.name.replace(' ', '-')}",
                resource_group_name=resource_group.name,
                location=resource_group.location,
            )

            # Step 9: Create default route for public subnet
            Route(
                self,
                f"RangePublicDefaultRoute-{vpc.name}",
                name="InternetRoute",
                resource_group_name=resource_group.name,
                route_table_name=public_route_table.name,
                address_prefix="0.0.0.0/0",
                next_hop_type="Internet",
            )

            # Step 10: Associate Route Table with Public Subnet
            SubnetRouteTableAssociation(
                self,
                f"RangePublicSubnetRouteAssociation-{vpc.name}",
                subnet_id=public_subnet.id,
                route_table_id=public_route_table.id,
            )

            # Step 11: Create Public IP for Jump Box
            jumpbox_public_ip = PublicIp(
                self,
                f"JumpBoxPublicIP-{vpc.name}",
                name=f"JumpBoxPublicIP-{vpc.name.replace(' ', '-')}",
                resource_group_name=resource_group.name,
                location=resource_group.location,
                allocation_method="Static",
            )

            # Step 12: Create Network Interface for Jump Box
            jumpbox_nic = NetworkInterface(
                self,
                f"JumpBoxNIC-{vpc.name}",
                name=f"JumpBoxNIC-{vpc.name.replace(' ', '-')}",
                resource_group_name=resource_group.name,
                location=resource_group.location,
                # enable_ip_forwarding is not supported in this version
                ip_configuration=[
                    {
                        "name": "primary",
                        "subnetId": public_subnet.id,
                        "privateIpAddressAllocation": "Dynamic",
                        "publicIpAddressId": jumpbox_public_ip.id,
                    }
                ],
            )

            # Step 13: Create Jump Box VM with SSH key authentication

            VirtualMachine(
                self,
                f"JumpBoxVM-{vpc.name}",
                name=f"JumpBox-{vpc.name.replace(' ', '-')}",
                resource_group_name=resource_group.name,
                location=resource_group.location,
                network_interface_ids=[jumpbox_nic.id],
                vm_size="Standard_B1s",
                delete_os_disk_on_termination=True,
                os_profile={
                    "computer_name": "jumpbox",
                    "admin_username": "azureuser",
                },
                os_profile_linux_config={
                    "disable_password_authentication": True,
                    "ssh_keys": [
                        {
                            "keyData": user_public_key,
                            "path": "/home/azureuser/.ssh/authorized_keys",
                        }
                    ],
                },
                storage_image_reference={
                    "publisher": "Canonical",
                    "offer": "0001-com-ubuntu-server-focal",
                    "sku": "20_04-lts-gen2",
                    "version": "latest",
                },
                storage_os_disk={
                    "name": f"JumpBox-OSDisk-{vpc.name.replace(' ', '-')}",
                    "caching": "ReadWrite",
                    "create_option": "FromImage",
                    "managed_disk_type": "Standard_LRS",
                },
            )

            # Step 14: Create Network Security Group for Private Subnets
            private_nsg = NetworkSecurityGroup(
                self,
                f"RangePrivateNSG-{vpc.name}",
                name=f"RangePrivateNSG-{vpc.name.replace(' ', '-')}",
                resource_group_name=resource_group.name,
                location=resource_group.location,
            )

            # Step 15: Create NSG Rules for private subnets

            # Allow inbound traffic from Jump Box
            NetworkSecurityRule(
                self,
                f"RangeAllowFromJumpBox-{vpc.name}",
                name="AllowFromJumpBox",
                resource_group_name=resource_group.name,
                network_security_group_name=private_nsg.name,
                priority=100,
                direction="Inbound",
                access="Allow",
                protocol="*",
                source_port_range="*",
                destination_port_range="*",
                source_address_prefix=public_subnet_cidr,
                destination_address_prefix="*",
            )

            # Allow all outbound traffic
            NetworkSecurityRule(
                self,
                f"RangeAllowAllOutbound-{vpc.name}",
                name="AllowAllOutbound",
                resource_group_name=resource_group.name,
                network_security_group_name=private_nsg.name,
                priority=100,
                direction="Outbound",
                access="Allow",
                protocol="*",
                source_port_range="*",
                destination_port_range="*",
                source_address_prefix="*",
                destination_address_prefix="*",
            )

            # Create a Public IP for the NAT Gateway
            nat_gateway_public_ip = PublicIp(
                self,
                f"NatGatewayPublicIP-{vpc.name}",
                name=f"NatGatewayIP-{vpc.name.replace(' ', '-')}",
                resource_group_name=resource_group.name,
                location=resource_group.location,
                allocation_method="Static",
                sku="Standard",
            )

            # Create the NAT Gateway
            nat_gateway = NatGateway(
                self,
                f"NatGateway-{vpc.name}",
                name=f"NatGateway-{vpc.name.replace(' ', '-')}",
                resource_group_name=resource_group.name,
                location=resource_group.location,
                sku_name="Standard",
                idle_timeout_in_minutes=10,
            )

            # Associate the Public IP with the NAT Gateway
            NatGatewayPublicIpAssociation(
                self,
                f"NatGatewayIpAssociation-{vpc.name}",
                nat_gateway_id=nat_gateway.id,
                public_ip_address_id=nat_gateway_public_ip.id,
            )

            # Create Route Table for private subnets
            private_route_table = RouteTable(
                self,
                f"RangePrivateRouteTable-{vpc.name}",
                name=f"RangePrivateRouteTable-{vpc.name.replace(' ', '-')}",
                resource_group_name=resource_group.name,
                location=resource_group.location,
            )

            # Add default route for internet access through Internet (NAT Gateway will handle this)
            # Azure's NAT Gateway doesn't require specific routes - it works at the subnet level
            Route(
                self,
                f"RangePrivateDefaultRoute-{vpc.name}",
                name="InternetRouteViaNAT",
                resource_group_name=resource_group.name,
                route_table_name=private_route_table.name,
                address_prefix="0.0.0.0/0",
                next_hop_type="Internet",
            )

            # Step 17: Create private subnets with their respective VMs
            for subnet in vpc.subnets:
                private_subnet = Subnet(
                    self,
                    f"{subnet.name}-{vpc.name}",
                    name=f"{subnet.name.replace(' ', '-')}-{vpc.name.replace(' ', '-')}",
                    resource_group_name=resource_group.name,
                    virtual_network_name=vnet.name,
                    address_prefixes=[str(subnet.cidr)],
                )

                # Associate NSG with Private Subnet
                SubnetNetworkSecurityGroupAssociation(
                    self,
                    f"{subnet.name}-NSGAssociation-{vpc.name}",
                    subnet_id=private_subnet.id,
                    network_security_group_id=private_nsg.id,
                )

                # Associate Route Table with Private Subnet
                SubnetRouteTableAssociation(
                    self,
                    f"{subnet.name}-RouteAssociation-{vpc.name}",
                    subnet_id=private_subnet.id,
                    route_table_id=private_route_table.id,
                )

                # Associate the subnet with the NAT Gateway for outbound internet access
                SubnetNatGatewayAssociation(
                    self,
                    f"{subnet.name}-NatGatewayAssociation-{vpc.name}",
                    subnet_id=private_subnet.id,
                    nat_gateway_id=nat_gateway.id,
                )

                # Create VMs in the subnet
                for host in subnet.hosts:
                    # Get OS image details from URN
                    os_urn = AZURE_OS_MAP[
                        host.os
                    ]  # Format: Publisher:Offer:Sku:Version
                    os_parts = os_urn.split(":")
                    publisher = os_parts[0]
                    offer = os_parts[1]
                    sku = os_parts[2]
                    version = os_parts[3]

                    # Create Network Interface for the VM
                    vm_nic = NetworkInterface(
                        self,
                        f"{host.hostname}-NIC-{vpc.name}",
                        name=f"{host.hostname.replace(' ', '-')}-NIC-{vpc.name.replace(' ', '-')}",
                        resource_group_name=resource_group.name,
                        location=resource_group.location,
                        # enable_ip_forwarding is not supported in this version
                        ip_configuration=[
                            {
                                "name": "primary",
                                "subnetId": private_subnet.id,
                                "privateIpAddressAllocation": "Dynamic",
                            }
                        ],
                    )

                    # Create the VM with SSH key authentication

                    VirtualMachine(
                        self,
                        f"{host.hostname}-{vpc.name}",
                        name=f"{host.hostname.replace(' ', '-')}-{vpc.name.replace(' ', '-')}",
                        resource_group_name=resource_group.name,
                        location=resource_group.location,
                        network_interface_ids=[vm_nic.id],
                        vm_size=AZURE_SPEC_MAP[host.spec],
                        delete_os_disk_on_termination=True,
                        os_profile={
                            "computer_name": host.hostname,
                            "admin_username": "azureuser",
                        },
                        os_profile_linux_config={
                            "disable_password_authentication": True,
                            "ssh_keys": [
                                {
                                    "keyData": user_public_key,
                                    "path": "/home/azureuser/.ssh/authorized_keys",
                                }
                            ],
                        },
                        storage_image_reference={
                            "publisher": publisher,
                            "offer": offer,
                            "sku": sku,
                            "version": version,
                        },
                        storage_os_disk={
                            "name": f"{host.hostname.replace(' ', '-')}-OSDisk-{vpc.name.replace(' ', '-')}",
                            "caching": "ReadWrite",
                            "create_option": "FromImage",
                            "managed_disk_type": "Standard_LRS",
                        },
                    )
