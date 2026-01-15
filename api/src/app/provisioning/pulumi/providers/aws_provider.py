import logging
from typing import Callable

import pulumi
import pulumi.automation as auto

from ....enums.operating_systems import AWS_OS_MAP
from ....enums.regions import AWS_REGION_MAP, OpenLabsRegion
from ....enums.specs import AWS_SPEC_MAP
from ....schemas.range_schemas import BlueprintRangeSchema, DeployedRangeSchema
from ....schemas.secret_schema import SecretSchema
from ....utils.crypto import generate_range_rsa_key_pair
from ....utils.name_utils import normalize_name
from ..providers.protocol import PulumiProvider

# Configure logging
logger = logging.getLogger(__name__)


class AWSProvider(PulumiProvider):
    """AWS-specific Pulumi provider implementation."""

    def get_pulumi_program(
        self,
        stack_name: str,
        range_obj: BlueprintRangeSchema | DeployedRangeSchema,
    ) -> Callable[[], None]:
        """Return the Pulumi program function for AWS infrastructure.

        Args:
            range_obj: Blueprint or deployed range object
            region: Cloud region for deployment
            secrets: Cloud provider credentials
            stack_name: Name of the Pulumi stack

        Returns:
            Pulumi program function that defines infrastructure

        """

        def pulumi_program() -> None:
            # Import pulumi_aws inside the program function to ensure it's available
            # in Pulumi's inline execution context
            import pulumi_aws as aws  # noqa: PLC0415, I001

            # Import resource submodules - these work consistently across environments
            # The resources are in submodules like ec2.key_pair, ec2.vpc, etc.
            from pulumi_aws.ec2 import (  # noqa: PLC0415
                eip,
                instance,
                internet_gateway,
                key_pair,
                nat_gateway,
                route,
                route_table,
                route_table_association,
                security_group,
                subnet,
                vpc,
            )
            from pulumi_aws.ec2transitgateway import (  # noqa: PLC0415
                route as tgw_route,
                transit_gateway,
                vpc_attachment,
            )

            # Get AWS configuration from Pulumi config
            config = pulumi.Config("aws")
            aws_region = config.require("region")

            # Try to get credentials from Pulumi config first (more secure)
            # Fall back to environment variables if not in config
            try:
                aws_access_key = config.require_secret("accessKey")
                aws_secret_key = config.require_secret("secretKey")

                # Create explicit AWS provider with credentials from config
                provider = aws.Provider(
                    "aws-provider",
                    region=aws_region,
                    access_key=aws_access_key,
                    secret_key=aws_secret_key,
                )
            except pulumi.ConfigMissingError:
                # Credentials not in config, rely on environment variables
                # AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY set in LocalWorkspaceOptions
                provider = aws.Provider(
                    "aws-provider",
                    region=aws_region,
                    # Credentials will be read from environment variables
                )

            # Step 1: Create the key access to all instances provisioned on AWS
            range_private_key, range_public_key = generate_range_rsa_key_pair()
            key_pair_name = f"{stack_name}-key-pair"
            key_pair_resource = key_pair.KeyPair(
                key_pair_name,
                key_name=f"{stack_name}-pulumi-public-key",
                public_key=range_public_key,
                tags={"Name": key_pair_name},
                opts=pulumi.ResourceOptions(provider=provider),
            )

            pulumi.export(
                f"{stack_name}-range-private-key",
                pulumi.Output.secret(range_private_key),
            )

            # Step 2: Create public vpc for jumpbox
            jumpbox_vpc_name = f"{stack_name}-jumpbox-vpc"
            jumpbox_vpc = vpc.Vpc(
                jumpbox_vpc_name,
                cidr_block="10.255.0.0/16",
                enable_dns_support=True,
                enable_dns_hostnames=True,
                tags={"Name": jumpbox_vpc_name},
                opts=pulumi.ResourceOptions(provider=provider),
            )

            # Step 3: Create public subnet for jumpbox
            jumpbox_public_subnet_name = f"{stack_name}-jumpbox-public-subnet"
            jumpbox_public_subnet = subnet.Subnet(
                jumpbox_public_subnet_name,
                vpc_id=jumpbox_vpc.id,
                cidr_block="10.255.99.0/24",
                availability_zone="us-east-1a",
                map_public_ip_on_launch=True,
                tags={"Name": jumpbox_public_subnet_name},
                opts=pulumi.ResourceOptions(provider=provider),
            )

            # Step 4: Create Security Group and Rules for Jump Box
            jumpbox_sg_name = f"{stack_name}-jumpbox-security-group"
            jumpbox_sg = security_group.SecurityGroup(
                jumpbox_sg_name,
                vpc_id=jumpbox_vpc.id,
                tags={"Name": jumpbox_sg_name},
                ingress=[
                    security_group.SecurityGroupIngressArgs(
                        from_port=22,
                        to_port=22,
                        protocol="tcp",
                        cidr_blocks=["0.0.0.0/0"],
                    )
                ],
                egress=[
                    security_group.SecurityGroupEgressArgs(
                        from_port=0,
                        to_port=0,
                        protocol="-1",
                        cidr_blocks=["0.0.0.0/0"],
                    )
                ],
                opts=pulumi.ResourceOptions(provider=provider),
            )

            # Step 5: Create Jump Box
            jumpbox_instance_name = f"{stack_name}-jumpbox-instance"
            jumpbox = instance.Instance(
                jumpbox_instance_name,
                ami="ami-014f7ab33242ea43c",  # Amazon Ubuntu 20.04 AMI
                instance_type="t2.micro",
                subnet_id=jumpbox_public_subnet.id,
                vpc_security_group_ids=[jumpbox_sg.id],
                associate_public_ip_address=True,
                key_name=key_pair_resource.key_name,
                tags={"Name": jumpbox_instance_name},
                opts=pulumi.ResourceOptions(provider=provider),
            )

            pulumi.export(f"{stack_name}-jumpbox-resource-id", jumpbox.id)
            pulumi.export(
                f"{stack_name}-jumpbox-public-ip",
                pulumi.Output.secret(jumpbox.public_ip),
            )

            # Step 6: Create an Internet Gateway for Public jumpbox Subnet
            igw_name = f"{stack_name}-internet-gateway"
            igw = internet_gateway.InternetGateway(
                igw_name,
                vpc_id=jumpbox_vpc.id,
                tags={"Name": igw_name},
                opts=pulumi.ResourceOptions(provider=provider),
            )

            # Step 7: Create a NAT Gateway for range network with EIP
            eip_name = f"{stack_name}-nat-eip"
            eip_resource = eip.Eip(
                eip_name,
                domain="vpc",
                tags={"Name": eip_name},
                opts=pulumi.ResourceOptions(provider=provider),
            )

            nat_gateway_name = f"{stack_name}-nat-gateway"
            nat_gateway_resource = nat_gateway.NatGateway(
                nat_gateway_name,
                subnet_id=jumpbox_public_subnet.id,
                allocation_id=eip_resource.id,
                tags={"Name": nat_gateway_name},
                opts=pulumi.ResourceOptions(provider=provider),
            )

            # Step 8: Create Routing for Jumpbox
            jumpbox_route_table_name = f"{stack_name}-jumpbox-route-table"
            jumpbox_route_table = route_table.RouteTable(
                jumpbox_route_table_name,
                vpc_id=jumpbox_vpc.id,
                tags={"Name": jumpbox_route_table_name},
                opts=pulumi.ResourceOptions(provider=provider),
            )

            route.Route(
                f"{stack_name}-public-internet-route",
                route_table_id=jumpbox_route_table.id,
                destination_cidr_block="0.0.0.0/0",
                gateway_id=igw.id,
                opts=pulumi.ResourceOptions(provider=provider),
            )

            route_table_association.RouteTableAssociation(
                f"{stack_name}-public-route-association",
                subnet_id=jumpbox_public_subnet.id,
                route_table_id=jumpbox_route_table.id,
                opts=pulumi.ResourceOptions(provider=provider),
            )

            # Step 9: Create private subnet in the jumpbox vpc
            jumpbox_private_subnet_name = f"{stack_name}-jumpbox-private-subnet"
            jumpbox_vpc_private_subnet = subnet.Subnet(
                jumpbox_private_subnet_name,
                vpc_id=jumpbox_vpc.id,
                cidr_block="10.255.98.0/24",
                availability_zone="us-east-1a",
                map_public_ip_on_launch=False,
                tags={"Name": jumpbox_private_subnet_name},
                opts=pulumi.ResourceOptions(provider=provider),
            )

            # Step 10: Create Routing for range network (Using NAT gateway)
            nat_route_table_name = f"{stack_name}-private-route-table"
            nat_route_table = route_table.RouteTable(
                nat_route_table_name,
                vpc_id=jumpbox_vpc.id,
                tags={"Name": nat_route_table_name},
                opts=pulumi.ResourceOptions(provider=provider),
            )

            route.Route(
                f"{stack_name}-private-nat-route",
                route_table_id=nat_route_table.id,
                destination_cidr_block="0.0.0.0/0",
                nat_gateway_id=nat_gateway_resource.id,
                opts=pulumi.ResourceOptions(provider=provider),
            )

            route_table_association.RouteTableAssociation(
                f"{stack_name}-private-route-association",
                subnet_id=jumpbox_vpc_private_subnet.id,
                route_table_id=nat_route_table.id,
                opts=pulumi.ResourceOptions(provider=provider),
            )

            # Step 11: Create Transit Gateway to allow traffic to go anywhere in the range (connects all the range vpcs with each other)
            tgw_name = f"{stack_name}-transit-gateway"
            tgw = transit_gateway.TransitGateway(
                tgw_name,
                description="Transit Gateway for internal routing",
                tags={"Name": tgw_name},
                opts=pulumi.ResourceOptions(provider=provider),
            )

            # --- TGW Route to NAT Gateway (via Public VPC Attachment) ---
            # This route directs traffic destined for the internet (0.0.0.0/0) coming *from*
            # the range VPCs *towards* the Public VPC attachment ENI (which is in jumpbox_public_subnet inside jumpbox_vpc).
            # The new_vpc_private_route_table then directs it to the NAT GW.

            # --- Public VPC TGW Attachment ---
            # Step 12: Attach the jumpbox private subnet to the transit gateway
            # The jumpbox will be able to initiate communication with the range network to access the machines, but the range machines will
            # Not be able to initate communication back to the jumpbox (one-way)

            # Step 12: Attach the jumpbox private subnet to the transit gateway
            jumpbox_vpc_tgw_attachment_name = f"{stack_name}-public-vpc-tgw-attachment"
            jumpbox_vpc_tgw_attachment = vpc_attachment.VpcAttachment(
                jumpbox_vpc_tgw_attachment_name,
                subnet_ids=[jumpbox_vpc_private_subnet.id],
                transit_gateway_id=tgw.id,
                vpc_id=jumpbox_vpc.id,
                transit_gateway_default_route_table_association=True,
                transit_gateway_default_route_table_propagation=True,
                tags={"Name": jumpbox_vpc_tgw_attachment_name},
                opts=pulumi.ResourceOptions(provider=provider),
            )

            # Step 13: Add Routing to the Transit Gateway
            # Any traffic destined for the internet will route through the transit gateway to the jumpbox private subnet
            # From there the traffic will use the NAT routing table to route to the NAT gateway to access the internet
            tgw_internet_route_name = f"{stack_name}-tgw-internet-route"
            tgw_route.Route(
                tgw_internet_route_name,
                destination_cidr_block="0.0.0.0/0",
                transit_gateway_attachment_id=jumpbox_vpc_tgw_attachment.id,
                transit_gateway_route_table_id=tgw.association_default_route_table_id,
                opts=pulumi.ResourceOptions(provider=provider),
            )

            # Step 14: Create range VPCs, Subnets, and Hosts
            for vpc_obj in range_obj.vpcs:
                vpc_name = normalize_name(vpc_obj.name)
                vpc_prefix = f"{stack_name}-{vpc_name}"
                vpc_resource_name = f"{vpc_prefix}-vpc"

                # Create VPC
                range_vpc = vpc.Vpc(
                    vpc_resource_name,
                    cidr_block=str(vpc_obj.cidr),
                    enable_dns_support=True,
                    enable_dns_hostnames=True,
                    tags={"Name": vpc_resource_name},
                    opts=pulumi.ResourceOptions(provider=provider),
                )

                # Export VPC resource ID
                pulumi.export(f"{vpc_prefix}-resource-id", range_vpc.id)

                # Create security group for access to range hosts
                private_vpc_sg_name = f"{vpc_prefix}-shared-private-sg"
                private_vpc_sg = security_group.SecurityGroup(
                    private_vpc_sg_name,
                    vpc_id=range_vpc.id,
                    tags={"Name": "RangePrivateInternalSecurityGroup"},
                    ingress=[
                        security_group.SecurityGroupIngressArgs(
                            from_port=0,
                            to_port=0,
                            protocol="-1",
                            cidr_blocks=["10.255.99.0/24"],  # Allow from Jumpbox
                        ),
                        security_group.SecurityGroupIngressArgs(
                            from_port=0,
                            to_port=0,
                            protocol="-1",
                            cidr_blocks=["0.0.0.0/0"],  # Allow all internal traffic
                        ),
                    ],
                    egress=[
                        security_group.SecurityGroupEgressArgs(
                            from_port=0,
                            to_port=0,
                            protocol="-1",
                            cidr_blocks=["0.0.0.0/0"],  # Allow all outbound
                        ),
                    ],
                    opts=pulumi.ResourceOptions(provider=provider),
                )

                current_vpc_subnets = []

                for subnet_obj in vpc_obj.subnets:
                    subnet_name = normalize_name(subnet_obj.name)
                    subnet_prefix = f"{vpc_prefix}-{subnet_name}"
                    subnet_resource_name = f"{subnet_prefix}-subnet"

                    # Create Subnet
                    range_subnet = subnet.Subnet(
                        subnet_resource_name,
                        vpc_id=range_vpc.id,
                        cidr_block=str(subnet_obj.cidr),
                        availability_zone="us-east-1a",
                        map_public_ip_on_launch=False,
                        tags={"Name": subnet_resource_name},
                        opts=pulumi.ResourceOptions(provider=provider),
                    )

                    # Export Subnet resource ID
                    pulumi.export(f"{subnet_prefix}-resource-id", range_subnet.id)
                    current_vpc_subnets.append(range_subnet)

                    # Create EC2 instances in the subnet
                    for host in subnet_obj.hosts:
                        host_prefix = f"{subnet_prefix}-{host.hostname}"
                        host_resource_name = f"{host_prefix}-instance"

                        # Get AMI and instance type
                        ami = AWS_OS_MAP[host.os]
                        instance_type = AWS_SPEC_MAP[host.spec]

                        # Create Host Instance
                        host_instance = instance.Instance(
                            host_resource_name,
                            ami=ami,
                            instance_type=instance_type,
                            subnet_id=range_subnet.id,
                            vpc_security_group_ids=[private_vpc_sg.id],
                            associate_public_ip_address=False,
                            key_name=key_pair_resource.key_name,
                            tags={"Name": host_resource_name},
                            opts=pulumi.ResourceOptions(provider=provider),
                        )

                        # Export Host resource ID and private IP
                        pulumi.export(f"{host_prefix}-resource-id", host_instance.id)
                        pulumi.export(
                            f"{host_prefix}-ip-address", host_instance.private_ip
                        )

                # Step 15: Attach VPC to Transit Gateway
                private_vpc_tgw_attachment_name = (
                    f"{vpc_prefix}-private-vpc-tgw-attachment"
                )
                vpc_attachment.VpcAttachment(
                    private_vpc_tgw_attachment_name,
                    subnet_ids=[current_vpc_subnets[0].id],
                    transit_gateway_id=tgw.id,
                    vpc_id=range_vpc.id,
                    transit_gateway_default_route_table_association=True,
                    transit_gateway_default_route_table_propagation=True,
                    tags={"Name": private_vpc_tgw_attachment_name},
                    opts=pulumi.ResourceOptions(provider=provider),
                )

                # Step 16: Create Routing in range VPC (Routes to TGW to access other range VPCs or the internet via the NAT gateway)
                new_vpc_private_route_table_name = f"{vpc_prefix}-private-route-table"
                new_vpc_private_route_table = route_table.RouteTable(
                    new_vpc_private_route_table_name,
                    vpc_id=range_vpc.id,
                    tags={"Name": new_vpc_private_route_table_name},
                    opts=pulumi.ResourceOptions(provider=provider),
                )
                tgw_route_name = f"{vpc_prefix}-private-tgw-route"
                route.Route(
                    tgw_route_name,
                    route_table_id=new_vpc_private_route_table.id,
                    destination_cidr_block="0.0.0.0/0",
                    transit_gateway_id=tgw.id,
                    opts=pulumi.ResourceOptions(provider=provider),
                )

                # Associate VPC subnets with Route Table
                for i, created_subnet in enumerate(current_vpc_subnets):
                    route_table_association.RouteTableAssociation(
                        f"{vpc_prefix}-private-subnet-route-table-association-{i + 1}",
                        subnet_id=created_subnet.id,
                        route_table_id=new_vpc_private_route_table.id,
                        opts=pulumi.ResourceOptions(provider=provider),
                    )

                # Step 20: Create Routing in Jumpbox VPC
                # Add route to the Jumpbox VPC's Public route table
                route.Route(
                    f"{vpc_prefix}-public-rtb-to-private-vpc-route",
                    route_table_id=jumpbox_route_table.id,
                    destination_cidr_block=str(vpc_obj.cidr),
                    transit_gateway_id=tgw.id,
                    opts=pulumi.ResourceOptions(provider=provider),
                )
                # Add route to the Jumpbox VPC's NAT route table
                route.Route(
                    f"{vpc_prefix}-public-vpc-tgw-subnet-rtb-to-private-vpc-route",
                    route_table_id=nat_route_table.id,
                    destination_cidr_block=str(vpc_obj.cidr),
                    transit_gateway_id=tgw.id,
                    opts=pulumi.ResourceOptions(provider=provider),
                )

        return pulumi_program

    def has_secrets(self, secrets: SecretSchema) -> bool:
        """Check if AWS credentials are available.

        Args:
            secrets: Cloud provider credentials

        Returns:
            True if AWS credentials exist, False otherwise

        """
        return bool(
            hasattr(secrets, "aws_access_key")
            and hasattr(secrets, "aws_secret_key")
            and secrets.aws_access_key
            and secrets.aws_secret_key
        )

    def get_config_values(
        self,
        region: OpenLabsRegion,
        secrets: SecretSchema,
    ) -> dict[str, auto.ConfigValue]:
        """Return Pulumi configuration values for AWS.

        Args:
            region: Cloud region for deployment
            secrets: Cloud provider credentials

        Returns:
            Dict of Pulumi configuration values

        """
        if not self.has_secrets(secrets):
            msg = "AWS credentials are required"
            raise ValueError(msg)

        if secrets.aws_access_key is None or secrets.aws_secret_key is None:
            msg = "AWS access key and secret key must not be None"
            raise ValueError(msg)

        return {
            "aws:region": auto.ConfigValue(value=AWS_REGION_MAP[region]),
            "aws:accessKey": auto.ConfigValue(
                value=secrets.aws_access_key, secret=True
            ),
            "aws:secretKey": auto.ConfigValue(
                value=secrets.aws_secret_key, secret=True
            ),
        }

    def get_cred_env_vars(self, secrets: SecretSchema) -> dict[str, str]:
        """Return AWS credential environment variables.

        Args:
            secrets: Cloud provider credentials

        Returns:
            Dict of environment variables for cloud credentials

        """
        if not self.has_secrets(secrets):
            msg = "AWS credentials are required"
            raise ValueError(msg)

        if secrets.aws_access_key is None or secrets.aws_secret_key is None:
            msg = "AWS access key and secret key must not be None"
            raise ValueError(msg)

        return {
            "AWS_ACCESS_KEY_ID": secrets.aws_access_key,
            "AWS_SECRET_ACCESS_KEY": secrets.aws_secret_key,
        }


# Create a singleton instance
aws_provider = AWSProvider()
