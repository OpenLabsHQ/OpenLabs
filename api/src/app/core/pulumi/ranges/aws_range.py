import logging
from typing import Any

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
        state_data: dict[str, Any] | None = None,
    ) -> None:
        """Initialize AWS Pulumi range."""
        super().__init__(name, range_obj, region, secrets, description, state_data)

    def has_secrets(self) -> bool:
        """Check if AWS credentials are available."""
        return bool(
            hasattr(self.secrets, "aws_access_key")
            and hasattr(self.secrets, "aws_secret_key")
            and self.secrets.aws_access_key
            and self.secrets.aws_secret_key
        )

    def get_cred_env_vars(self) -> dict[str, Any]:
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

    def get_pulumi_program(self) -> callable:
        """Return the Pulumi program function for AWS infrastructure."""

        def pulumi_program():
            """Define AWS infrastructure using Pulumi."""
            # Step 1: Create the key access to all instances provisioned on AWS
            range_private_key, range_public_key = generate_range_rsa_key_pair()
            key_pair = aws.ec2.KeyPair(
                f"{self.deployed_range_name}-KeyPair",
                key_name=f"{self.deployed_range_name}-pulumi-public-key",
                public_key=range_public_key,
                tags={"Name": "pulumi-public-key"},
            )

            pulumi.export(f"{self.deployed_range_name}-private-key", range_private_key)

            # Step 2: Create public vpc for jumpbox
            jumpbox_vpc = aws.ec2.Vpc(
                f"{self.deployed_range_name}-JumpBoxVPC",
                cidr_block="10.255.0.0/16",
                enable_dns_support=True,
                enable_dns_hostnames=True,
                tags={"Name": "JumpBoxVPC"},
            )

            # Step 3: Create public subnet for jumpbox
            jumpbox_public_subnet = aws.ec2.Subnet(
                f"{self.deployed_range_name}-JumpBoxPublicSubnet",
                vpc_id=jumpbox_vpc.id,
                cidr_block="10.255.99.0/24",
                availability_zone="us-east-1a",
                map_public_ip_on_launch=True,
                tags={"Name": "JumpBoxVPCPublicSubnet"},
            )

            # Step 4: Create Security Group and Rules for Jump Box
            jumpbox_sg = aws.ec2.SecurityGroup(
                f"{self.deployed_range_name}-RangeJumpBoxSecurityGroup",
                vpc_id=jumpbox_vpc.id,
                tags={"Name": "RangeJumpBoxSecurityGroup"},
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
            jumpbox = aws.ec2.Instance(
                f"{self.deployed_range_name}-JumpBoxInstance",
                ami="ami-014f7ab33242ea43c",  # Amazon Ubuntu 20.04 AMI
                instance_type="t2.micro",
                subnet_id=jumpbox_public_subnet.id,
                vpc_security_group_ids=[jumpbox_sg.id],
                associate_public_ip_address=True,
                key_name=key_pair.key_name,
                tags={"Name": "JumpBox"},
            )

            pulumi.export(f"{self.deployed_range_name}-JumpboxPublicIp", jumpbox.public_ip)
            pulumi.export(f"{self.deployed_range_name}-JumpboxInstanceId", jumpbox.id)

            # Step 6: Create an Internet Gateway for Public jumpbox Subnet
            igw = aws.ec2.InternetGateway(
                f"{self.deployed_range_name}-RangeInternetGateway",
                vpc_id=jumpbox_vpc.id,
                tags={"Name": "RangeInternetGateway"},
            )

            # Step 7: Create a NAT Gateway for range network with EIP
            eip = aws.ec2.Eip(
                f"{self.deployed_range_name}-RangeNatEIP",
                domain="vpc",
                tags={"Name": "RangeNatEIP"},
            )

            nat_gateway = aws.ec2.NatGateway(
                f"{self.deployed_range_name}-RangeNatGateway",
                subnet_id=jumpbox_public_subnet.id,
                allocation_id=eip.id,
                tags={"Name": "RangeNatGateway"},
            )

            # Step 8: Create Routing for Jumpbox
            jumpbox_route_table = aws.ec2.RouteTable(
                f"{self.deployed_range_name}-JumpBoxRouteTable",
                vpc_id=jumpbox_vpc.id,
                tags={"Name": "RangePublicRouteTable"},
            )

            aws.ec2.Route(
                f"{self.deployed_range_name}-RangePublicInternetRoute",
                route_table_id=jumpbox_route_table.id,
                destination_cidr_block="0.0.0.0/0",
                gateway_id=igw.id,
            )

            aws.ec2.RouteTableAssociation(
                f"{self.deployed_range_name}-RangePublicRouteAssociation",
                subnet_id=jumpbox_public_subnet.id,
                route_table_id=jumpbox_route_table.id,
            )

            # Step 9: Create private subnet in the jumpbox vpc
            jumpbox_vpc_private_subnet = aws.ec2.Subnet(
                f"{self.deployed_range_name}-JumpBoxVPCPrivateSubnet",
                vpc_id=jumpbox_vpc.id,
                cidr_block="10.255.98.0/24",
                availability_zone="us-east-1a",
                map_public_ip_on_launch=False,
                tags={"Name": "JumpBoxVPCPrivateSubnet"},
            )

            # Step 10: Create Routing for range network (Using NAT gateway)
            nat_route_table = aws.ec2.RouteTable(
                f"{self.deployed_range_name}-RangePrivateRouteTable",
                vpc_id=jumpbox_vpc.id,
                tags={"Name": "RangePrivateRouteTable"},
            )

            aws.ec2.Route(
                f"{self.deployed_range_name}-RangePrivateNatRoute",
                route_table_id=nat_route_table.id,
                destination_cidr_block="0.0.0.0/0",
                nat_gateway_id=nat_gateway.id,
            )

            aws.ec2.RouteTableAssociation(
                f"{self.deployed_range_name}-RangePrivateRouteAssociation",
                subnet_id=jumpbox_vpc_private_subnet.id,
                route_table_id=nat_route_table.id,
            )

            # Step 11: Create Transit Gateway
            tgw = aws.ec2transitgateway.TransitGateway(
                f"{self.deployed_range_name}-TransitGateway",
                description="Transit Gateway for internal routing",
                tags={"Name": "tgw"},
            )

            # Step 12: Attach the jumpbox private subnet to the transit gateway
            jumpbox_vpc_tgw_attachment = aws.ec2transitgateway.VpcAttachment(
                f"{self.deployed_range_name}-PublicVpcTgwAttachment",
                subnet_ids=[jumpbox_vpc_private_subnet.id],
                transit_gateway_id=tgw.id,
                vpc_id=jumpbox_vpc.id,
                transit_gateway_default_route_table_association=True,
                transit_gateway_default_route_table_propagation=True,
                tags={"Name": "public-vpc-tgw-attachment"},
            )

            # Step 13: Add Routing to the Transit Gateway
            aws.ec2transitgateway.Route(
                f"{self.deployed_range_name}-TgwInternetRoute",
                destination_cidr_block="0.0.0.0/0",
                transit_gateway_attachment_id=jumpbox_vpc_tgw_attachment.id,
                transit_gateway_route_table_id=tgw.association_default_route_table_id,
            )

            # Create Range vpcs, subnets, hosts
            for vpc in self.range_obj.vpcs:
                normalized_vpc_name = normalize_name(vpc.name)

                # Step 14: Create a VPC
                new_vpc = aws.ec2.Vpc(
                    f"{self.deployed_range_name}-{normalized_vpc_name}",
                    cidr_block=str(vpc.cidr),
                    enable_dns_support=True,
                    enable_dns_hostnames=True,
                    tags={"Name": normalized_vpc_name},
                )

                pulumi.export(
                    f"{self.deployed_range_name}-{normalized_vpc_name}-resource-id",
                    new_vpc.id,
                )

                # Step 15: Create security group for access to range hosts
                private_vpc_sg = aws.ec2.SecurityGroup(
                    f"{self.deployed_range_name}-{normalized_vpc_name}-SharedPrivateSG",
                    vpc_id=new_vpc.id,
                    tags={"Name": "RangePrivateInternalSecurityGroup"},
                    ingress=[
                        aws.ec2.SecurityGroupIngressArgs(
                            from_port=0,
                            to_port=0,
                            protocol="-1",
                            cidr_blocks=["10.255.99.0/24"],
                        ),
                        aws.ec2.SecurityGroupIngressArgs(
                            from_port=0,
                            to_port=0,
                            protocol="-1",
                            cidr_blocks=["0.0.0.0/0"],
                        ),
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

                current_vpc_subnets = []
                # Step 16: Create private subnets with their respective EC2 instances
                for subnet in vpc.subnets:
                    normalized_subnet_name = normalize_name(subnet.name)

                    new_subnet = aws.ec2.Subnet(
                        f"{self.deployed_range_name}-{normalized_vpc_name}-{normalized_subnet_name}",
                        vpc_id=new_vpc.id,
                        cidr_block=str(subnet.cidr),
                        availability_zone="us-east-1a",
                        tags={"Name": normalized_subnet_name},
                    )

                    pulumi.export(
                        f"{self.deployed_range_name}-{normalized_vpc_name}-{normalized_subnet_name}-resource-id",
                        new_subnet.id,
                    )

                    current_vpc_subnets.append(new_subnet)

                    # Create specified instances in the given subnet
                    for host in subnet.hosts:
                        ec2_instance = aws.ec2.Instance(
                            f"{self.deployed_range_name}-{normalized_vpc_name}-{normalized_subnet_name}-{host.hostname}",
                            ami=AWS_OS_MAP[host.os],
                            instance_type=AWS_SPEC_MAP[host.spec],
                            subnet_id=new_subnet.id,
                            vpc_security_group_ids=[private_vpc_sg.id],
                            key_name=key_pair.key_name,
                            tags={"Name": host.hostname},
                        )

                        pulumi.export(
                            f"{self.deployed_range_name}-{normalized_vpc_name}-{normalized_subnet_name}-{host.hostname}-resource-id",
                            ec2_instance.id,
                        )
                        pulumi.export(
                            f"{self.deployed_range_name}-{normalized_vpc_name}-{normalized_subnet_name}-{host.hostname}-private-ip",
                            ec2_instance.private_ip,
                        )

                # Step 17: Attach VPC to Transit Gateway
                aws.ec2transitgateway.VpcAttachment(
                    f"{self.deployed_range_name}-{normalized_vpc_name}-PrivateVpcTgwAttachment",
                    subnet_ids=[current_vpc_subnets[0].id],
                    transit_gateway_id=tgw.id,
                    vpc_id=new_vpc.id,
                    transit_gateway_default_route_table_association=True,
                    transit_gateway_default_route_table_propagation=True,
                    tags={"Name": f"{normalized_vpc_name}-private-vpc-tgw-attachment"},
                )

                # Step 18: Create Routing in range VPC
                new_vpc_private_route_table = aws.ec2.RouteTable(
                    f"{self.deployed_range_name}-{normalized_vpc_name}-PrivateRouteTable",
                    vpc_id=new_vpc.id,
                    tags={"Name": f"{normalized_vpc_name}-private-route-table"},
                )

                aws.ec2.Route(
                    f"{self.deployed_range_name}-{normalized_vpc_name}-PrivateTgwRoute",
                    route_table_id=new_vpc_private_route_table.id,
                    destination_cidr_block="0.0.0.0/0",
                    transit_gateway_id=tgw.id,
                )

                # Associate VPC subnets with Route Table
                for i, created_subnet in enumerate(current_vpc_subnets):
                    aws.ec2.RouteTableAssociation(
                        f"{self.deployed_range_name}-{normalized_vpc_name}-PrivateSubnetRouteTableAssociation_{i+1}",
                        subnet_id=created_subnet.id,
                        route_table_id=new_vpc_private_route_table.id,
                    )

                # Step 20: Create Routing in Jumpbox VPC
                aws.ec2.Route(
                    f"{self.deployed_range_name}-{normalized_vpc_name}-PublicRtbToPrivateVpcRoute",
                    route_table_id=jumpbox_route_table.id,
                    destination_cidr_block=new_vpc.cidr_block,
                    transit_gateway_id=tgw.id,
                )

                aws.ec2.Route(
                    f"{self.deployed_range_name}-{normalized_vpc_name}-PublicVpcTgwSubnetRtbToPrivateVpcRoute",
                    route_table_id=nat_route_table.id,
                    destination_cidr_block=new_vpc.cidr_block,
                    transit_gateway_id=tgw.id,
                )

        return pulumi_program