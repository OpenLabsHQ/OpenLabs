import logging
from typing import Callable

import pulumi
import pulumi.automation as auto
import pulumi_aws as aws

from ....enums.operating_systems import AWS_OS_MAP
from ....enums.regions import AWS_REGION_MAP, OpenLabsRegion
from ....enums.specs import AWS_SPEC_MAP
from ....schemas.range_schemas import BlueprintRangeSchema, DeployedRangeSchema
from ....schemas.secret_schema import SecretSchema
from ....utils.crypto import generate_range_rsa_key_pair
from ....utils.name_utils import normalize_name
from .base_range import AbstractBasePulumiRange

# Configure logging
logger = logging.getLogger(__name__)


class AWSPulumiRange(AbstractBasePulumiRange):
    """AWS-specific Pulumi range implementation."""

    def __init__(
        self,
        name: str,
        range_obj: BlueprintRangeSchema | DeployedRangeSchema,
        region: OpenLabsRegion,
        secrets: SecretSchema,
        description: str,
        deployment_id: str,
    ) -> None:
        """Initialize AWS Pulumi range."""
        super().__init__(name, range_obj, region, secrets, description, deployment_id)

    def has_secrets(self) -> bool:
        """Check if AWS credentials are available."""
        return bool(
            hasattr(self.secrets, "aws_access_key")
            and hasattr(self.secrets, "aws_secret_key")
            and self.secrets.aws_access_key
            and self.secrets.aws_secret_key
        )

    def get_cred_env_vars(self) -> dict[str, str]:
        """Return AWS credential environment variables."""
        return {
            "AWS_ACCESS_KEY_ID": self.secrets.aws_access_key,
            "AWS_SECRET_ACCESS_KEY": self.secrets.aws_secret_key,
        }

    def get_config_values(self) -> dict[str, auto.ConfigValue]:
        """Return Pulumi configuration values for AWS."""
        return {
            "aws:region": auto.ConfigValue(value=AWS_REGION_MAP[self.region]),
            "aws:accessKey": auto.ConfigValue(
                value=self.secrets.aws_access_key, secret=True
            ),
            "aws:secretKey": auto.ConfigValue(
                value=self.secrets.aws_secret_key, secret=True
            ),
        }

    def get_pulumi_program(self) -> Callable[[], None]:
        """Return the Pulumi program function for AWS infrastructure."""

        def pulumi_program():
            stack_name = self.stack_name

            # Step 1: Create the key access to all instances provisioned on AWS
            range_private_key, range_public_key = generate_range_rsa_key_pair()
            key_pair_name = f"{stack_name}-key-pair"
            key_pair = aws.ec2.KeyPair(
                key_pair_name,
                key_name=f"{stack_name}-pulumi-public-key",
                public_key=range_public_key,
                tags={"Name": key_pair_name},
            )

            pulumi.export(
                f"{stack_name}-range-private-key",
                pulumi.Output.secret(range_private_key),
            )

            # Step 2: Create public vpc for jumpbox
            jumpbox_vpc_name = f"{stack_name}-jumpbox-vpc"
            jumpbox_vpc = aws.ec2.Vpc(
                jumpbox_vpc_name,
                cidr_block="10.255.0.0/16",
                enable_dns_support=True,
                enable_dns_hostnames=True,
                tags={"Name": jumpbox_vpc_name},
            )

            # Step 3: Create public subnet for jumpbox
            jumpbox_public_subnet_name = f"{stack_name}-jumpbox-public-subnet"
            jumpbox_public_subnet = aws.ec2.Subnet(
                jumpbox_public_subnet_name,
                vpc_id=jumpbox_vpc.id,
                cidr_block="10.255.99.0/24",
                availability_zone="us-east-1a",
                map_public_ip_on_launch=True,
                tags={"Name": jumpbox_public_subnet_name},
            )

            # Step 4: Create Security Group and Rules for Jump Box
            jumpbox_sg_name = f"{stack_name}-jumpbox-security-group"
            jumpbox_sg = aws.ec2.SecurityGroup(
                jumpbox_sg_name,
                vpc_id=jumpbox_vpc.id,
                tags={"Name": jumpbox_sg_name},
                ingress=[
                    aws.ec2.SecurityGroupIngressArgs(
                        from_port=22,
                        to_port=22,
                        protocol="tcp",
                        cidr_blocks=["0.0.0.0/0"],
                    )
                ],
                egress=[
                    aws.ec2.SecurityGroupEgressArgs(
                        from_port=0,
                        to_port=0,
                        protocol="-1",
                        cidr_blocks=["0.0.0.0/0"],
                    )
                ],
            )

            # Step 5: Create Jump Box
            jumpbox_instance_name = f"{stack_name}-jumpbox-instance"
            jumpbox = aws.ec2.Instance(
                jumpbox_instance_name,
                ami="ami-014f7ab33242ea43c",  # Amazon Ubuntu 20.04 AMI
                instance_type="t2.micro",
                subnet_id=jumpbox_public_subnet.id,
                vpc_security_group_ids=[jumpbox_sg.id],
                associate_public_ip_address=True,
                key_name=key_pair.key_name,
                tags={"Name": jumpbox_instance_name},
            )

            pulumi.export(f"{stack_name}-jumpbox-resource-id", jumpbox.id)
            pulumi.export(
                f"{stack_name}-jumpbox-public-ip",
                pulumi.Output.secret(jumpbox.public_ip),
            )

            # Step 6: Create an Internet Gateway for Public jumpbox Subnet
            igw_name = f"{stack_name}-internet-gateway"
            igw = aws.ec2.InternetGateway(
                igw_name,
                vpc_id=jumpbox_vpc.id,
                tags={"Name": igw_name},
            )

            # Step 7: Create a NAT Gateway for range network with EIP
            eip_name = f"{stack_name}-nat-eip"
            eip = aws.ec2.Eip(
                eip_name,
                domain="vpc",
                tags={"Name": eip_name},
            )

            nat_gateway_name = f"{stack_name}-nat-gateway"
            nat_gateway = aws.ec2.NatGateway(
                nat_gateway_name,
                subnet_id=jumpbox_public_subnet.id,
                allocation_id=eip.id,
                tags={"Name": nat_gateway_name},
            )

            # Step 8: Create Routing for Jumpbox
            jumpbox_route_table_name = f"{stack_name}-jumpbox-route-table"
            jumpbox_route_table = aws.ec2.RouteTable(
                jumpbox_route_table_name,
                vpc_id=jumpbox_vpc.id,
                tags={"Name": jumpbox_route_table_name},
            )

            aws.ec2.Route(
                f"{stack_name}-public-internet-route",
                route_table_id=jumpbox_route_table.id,
                destination_cidr_block="0.0.0.0/0",
                gateway_id=igw.id,
            )

            aws.ec2.RouteTableAssociation(
                f"{stack_name}-public-route-association",
                subnet_id=jumpbox_public_subnet.id,
                route_table_id=jumpbox_route_table.id,
            )

            # Step 9: Create private subnet in the jumpbox vpc
            jumpbox_private_subnet_name = f"{stack_name}-jumpbox-private-subnet"
            jumpbox_vpc_private_subnet = aws.ec2.Subnet(
                jumpbox_private_subnet_name,
                vpc_id=jumpbox_vpc.id,
                cidr_block="10.255.98.0/24",
                availability_zone="us-east-1a",
                map_public_ip_on_launch=False,
                tags={"Name": jumpbox_private_subnet_name},
            )

            # Step 10: Create Routing for range network (Using NAT gateway)
            nat_route_table_name = f"{stack_name}-private-route-table"
            nat_route_table = aws.ec2.RouteTable(
                nat_route_table_name,
                vpc_id=jumpbox_vpc.id,
                tags={"Name": nat_route_table_name},
            )

            aws.ec2.Route(
                f"{stack_name}-private-nat-route",
                route_table_id=nat_route_table.id,
                destination_cidr_block="0.0.0.0/0",
                nat_gateway_id=nat_gateway.id,
            )

            aws.ec2.RouteTableAssociation(
                f"{stack_name}-private-route-association",
                subnet_id=jumpbox_vpc_private_subnet.id,
                route_table_id=nat_route_table.id,
            )

            # Step 11: Create range VPCs, Subnets, and Hosts
            for vpc in self.range_obj.vpcs:
                vpc_name = normalize_name(vpc.name)
                vpc_prefix = f"{stack_name}-{vpc_name}"
                vpc_resource_name = f"{vpc_prefix}-vpc"

                # Create VPC
                range_vpc = aws.ec2.Vpc(
                    vpc_resource_name,
                    cidr_block=str(vpc.cidr),
                    enable_dns_support=True,
                    enable_dns_hostnames=True,
                    tags={"Name": vpc_resource_name},
                )

                # Export VPC resource ID
                pulumi.export(f"{vpc_prefix}-resource-id", range_vpc.id)

                for subnet in vpc.subnets:
                    subnet_name = normalize_name(subnet.name)
                    subnet_prefix = f"{vpc_prefix}-{subnet_name}"
                    subnet_resource_name = f"{subnet_prefix}-subnet"

                    # Create Subnet
                    range_subnet = aws.ec2.Subnet(
                        subnet_resource_name,
                        vpc_id=range_vpc.id,
                        cidr_block=str(subnet.cidr),
                        availability_zone="us-east-1a",
                        map_public_ip_on_launch=False,
                        tags={"Name": subnet_resource_name},
                    )

                    # Create Route Table for Subnet (basic local routing)
                    subnet_route_table_name = f"{subnet_prefix}-route-table"
                    subnet_route_table = aws.ec2.RouteTable(
                        subnet_route_table_name,
                        vpc_id=range_vpc.id,
                        tags={"Name": subnet_route_table_name},
                    )

                    # Associate Route Table with Subnet
                    aws.ec2.RouteTableAssociation(
                        f"{subnet_prefix}-route-association",
                        subnet_id=range_subnet.id,
                        route_table_id=subnet_route_table.id,
                    )

                    # Export Subnet resource ID
                    pulumi.export(f"{subnet_prefix}-resource-id", range_subnet.id)

                    for host in subnet.hosts:
                        host_prefix = f"{subnet_prefix}-{host.hostname}"
                        host_resource_name = f"{host_prefix}-instance"

                        # Create Security Group for Host
                        host_sg_name = f"{host_prefix}-security-group"
                        host_sg = aws.ec2.SecurityGroup(
                            host_sg_name,
                            vpc_id=range_vpc.id,
                            tags={"Name": host_sg_name},
                            ingress=[
                                aws.ec2.SecurityGroupIngressArgs(
                                    from_port=22,
                                    to_port=22,
                                    protocol="tcp",
                                    cidr_blocks=["10.255.0.0/16"],
                                )
                            ],
                            egress=[
                                aws.ec2.SecurityGroupEgressArgs(
                                    from_port=0,
                                    to_port=0,
                                    protocol="-1",
                                    cidr_blocks=["0.0.0.0/0"],
                                )
                            ],
                        )

                        # Get AMI and instance type
                        ami = AWS_OS_MAP[host.os]
                        instance_type = AWS_SPEC_MAP[host.spec]

                        # Create Host Instance
                        host_instance = aws.ec2.Instance(
                            host_resource_name,
                            ami=ami,
                            instance_type=instance_type,
                            subnet_id=range_subnet.id,
                            vpc_security_group_ids=[host_sg.id],
                            associate_public_ip_address=False,
                            key_name=key_pair.key_name,
                            tags={"Name": host_resource_name},
                        )

                        # Export Host resource ID and private IP
                        pulumi.export(f"{host_prefix}-resource-id", host_instance.id)
                        pulumi.export(
                            f"{host_prefix}-ip-address", host_instance.private_ip
                        )

        return pulumi_program
