from cdktf import TerraformOutput
from cdktf_cdktf_provider_aws.ec2_transit_gateway import Ec2TransitGateway
from cdktf_cdktf_provider_aws.ec2_transit_gateway_route import Ec2TransitGatewayRoute
from cdktf_cdktf_provider_aws.ec2_transit_gateway_vpc_attachment import (
    Ec2TransitGatewayVpcAttachment,
)
from cdktf_cdktf_provider_aws.eip import Eip
from cdktf_cdktf_provider_aws.instance import Instance
from cdktf_cdktf_provider_aws.internet_gateway import InternetGateway
from cdktf_cdktf_provider_aws.key_pair import KeyPair
from cdktf_cdktf_provider_aws.nat_gateway import NatGateway
from cdktf_cdktf_provider_aws.provider import AwsProvider
from cdktf_cdktf_provider_aws.route import Route
from cdktf_cdktf_provider_aws.route_table import RouteTable
from cdktf_cdktf_provider_aws.route_table_association import RouteTableAssociation
from cdktf_cdktf_provider_aws.security_group import SecurityGroup
from cdktf_cdktf_provider_aws.security_group_rule import SecurityGroupRule
from cdktf_cdktf_provider_aws.subnet import Subnet
from cdktf_cdktf_provider_aws.vpc import Vpc

from ....enums.operating_systems import AWS_OS_MAP
from ....enums.regions import AWS_REGION_MAP, OpenLabsRegion
from ....enums.specs import AWS_SPEC_MAP
from ....schemas.range_schemas import BlueprintRangeSchema, DeployedRangeSchema
from ....utils.cdktf_utils import normalize_resource_name
from ....utils.crypto import generate_range_rsa_key_pair
from .base_stack import AbstractBaseStack


class AWSStack(AbstractBaseStack):
    """Stack for generating terraform for AWS."""

    def build_resources(
        self,
        range_obj: BlueprintRangeSchema | DeployedRangeSchema,
        region: OpenLabsRegion,
        range_name: str,
    ) -> None:
        """Initialize AWS terraform stack.

        Args:
        ----
            range_obj (BlueprintRangeSchema | DeployedRangeSchema): Blueprint range object to build terraform for.
            region (OpenLabsRegion): Support OpenLabs cloud region.
            range_name (str): Name of range to deploy. Range name + unique ID.

        Returns:
        -------
            None

        """
        AwsProvider(
            self,
            "AWS",
            region=AWS_REGION_MAP[region],
        )

        # Step 1: Create the key access to all instances provisioned on AWS
        # Generate RSA key pair
        range_private_key, range_public_key = generate_range_rsa_key_pair()
        key_pair = KeyPair(
            self,
            f"{range_name}-KeyPair",
            key_name=f"{range_name}-cdktf-public-key",
            public_key=range_public_key,
            tags={"Name": "cdktf-public-key"},
        )

        TerraformOutput(
            self,
            f"{range_name}-private-key",
            value=range_private_key,
            description="Private key to access range machines",
            sensitive=True,
        )

        # Step 2: Create public vpc for jumpbox
        jumpbox_vpc = Vpc(
            self,
            f"{range_name}-JumpBoxVPC",
            cidr_block="10.255.0.0/16",
            enable_dns_support=True,
            enable_dns_hostnames=True,
            tags={"Name": "JumpBoxVPC"},
        )

        # Step 3: Create public subnet for jumpbox
        jumpbox_public_subnet = Subnet(
            self,
            f"{range_name}-JumpBoxPublicSubnet",
            vpc_id=jumpbox_vpc.id,
            cidr_block="10.255.99.0/24",
            availability_zone="us-east-1a",
            map_public_ip_on_launch=True,
            tags={"Name": "JumpBoxVPCPublicSubnet"},
        )

        # Step 4: Create Security Group and Rules for Jump Box (only allow SSH directly into jump box, for now)
        jumpbox_sg = SecurityGroup(
            self,
            f"{range_name}-RangeJumpBoxSecurityGroup",
            vpc_id=jumpbox_vpc.id,
            tags={"Name": "RangeJumpBoxSecurityGroup"},
        )
        SecurityGroupRule(
            self,
            f"{range_name}-RangeAllowJumpBoxSSHFromInternet",
            type="ingress",
            from_port=22,
            to_port=22,
            protocol="tcp",
            cidr_blocks=["0.0.0.0/0"],  # Allow SSH from anywhere
            security_group_id=jumpbox_sg.id,
        )
        SecurityGroupRule(
            self,
            f"{range_name}-RangeJumpBoxAllowOutbound",
            type="egress",
            from_port=0,
            to_port=0,
            protocol="-1",
            cidr_blocks=["0.0.0.0/0"],
            security_group_id=jumpbox_sg.id,
        )

        # Step 5: Create Jump Box
        jumpbox = Instance(
            self,
            f"{range_name}-JumpBoxInstance",
            ami="ami-014f7ab33242ea43c",  # Amazon Ubuntu 20.04 AMI
            instance_type="t2.micro",
            subnet_id=jumpbox_public_subnet.id,
            vpc_security_group_ids=[jumpbox_sg.id],
            associate_public_ip_address=True,  # Ensures public IP is assigned
            key_name=key_pair.key_name,  # Use the generated key pair
            tags={"Name": "JumpBox"},
        )

        TerraformOutput(
            self,
            f"{range_name}-JumpboxPublicIp",
            value=jumpbox.public_ip,
            description="Public IP address of the Jumpbox instance",
            sensitive=True,
        )
        TerraformOutput(
            self,
            f"{range_name}-JumpboxInstanceId",
            value=jumpbox.id,
            description="Instance ID of the Jumpbox instance",
            sensitive=True,
        )

        # Step 6: Create an Internet Gateway for Public jumpbox Subnet -> this is the only way into the range from the internet
        igw = InternetGateway(
            self,
            f"{range_name}-RangeInternetGateway",
            vpc_id=jumpbox_vpc.id,
            tags={"Name": "RangeInternetGateway"},
        )

        # Step 7: Create a NAT Gateway for range network with EIP (allow the range to have internet access for downloading tools, etc.)
        # Elastic IP for NAT Gateway
        eip = Eip(self, f"{range_name}-RangeNatEIP", tags={"Name": "RangeNatEIP"})

        nat_gateway = NatGateway(
            self,
            f"{range_name}-RangeNatGateway",
            subnet_id=jumpbox_public_subnet.id,  # NAT must be in a public subnet
            allocation_id=eip.id,
            tags={"Name": "RangeNatGateway"},
        )

        # Step 8: Create Routing for Jumpbox (table, route, route assoication with jumpbox public subnet)
        jumpbox_route_table = RouteTable(
            self,
            f"{range_name}-JumpBoxRouteTable",
            vpc_id=jumpbox_vpc.id,
            tags={"Name": "RangePublicRouteTable"},
        )

        igw_route = Route(  # noqa: F841
            self,
            f"{range_name}-RangePublicInternetRoute",
            route_table_id=jumpbox_route_table.id,
            destination_cidr_block="0.0.0.0/0",  # Allow internet access
            gateway_id=igw.id,
        )

        public_rt_assoc = RouteTableAssociation(  # noqa: F841
            self,
            f"{range_name}-RangePublicRouteAssociation",
            subnet_id=jumpbox_public_subnet.id,
            route_table_id=jumpbox_route_table.id,
        )

        # Step 9: Create private subnet in the jumpbox vpc that will be used to route range network traffic to the NAT gateway
        # Thos goal of this is to keep the range traffic internal and do not allow access to it from the internet gateway
        jumpbox_vpc_private_subnet = Subnet(
            self,
            f"{range_name}-JumpBoxVPCPrivateSubnet",
            vpc_id=jumpbox_vpc.id,
            cidr_block="10.255.98.0/24",
            availability_zone="us-east-1a",
            map_public_ip_on_launch=False,
            tags={"Name": "JumpBoxVPCPrivateSubnet"},
        )

        # Step 10: Create Routing for range network (Using NAT gateway)
        nat_route_table = RouteTable(
            self,
            f"{range_name}-RangePrivateRouteTable",
            vpc_id=jumpbox_vpc.id,
            tags={"Name": "RangePrivateRouteTable"},
        )
        nat_route = Route(  # noqa: F841
            self,
            f"{range_name}-RangePrivateNatRoute",
            route_table_id=nat_route_table.id,
            destination_cidr_block="0.0.0.0/0",  # Allow internet access
            nat_gateway_id=nat_gateway.id,  # Route through NAT Gateway
        )
        private_rt_assoc = RouteTableAssociation(  # noqa: F841
            self,
            f"{range_name}-RangePrivateRouteAssociation",
            subnet_id=jumpbox_vpc_private_subnet.id,
            route_table_id=nat_route_table.id,
        )

        # Step 11: Create Transit Gateway to allow traffic to go anywhere in the range (connects all the range vpcs with each other)
        tgw = Ec2TransitGateway(
            self,
            f"{range_name}-TransitGateway",
            description="Transit Gateway for internal routing",
            tags={"Name": "tgw"},
        )

        # --- TGW Route to NAT Gateway (via Public VPC Attachment) ---
        # This route directs traffic destined for the internet (0.0.0.0/0) coming *from*
        # the range VPCs *towards* the Public VPC attachment ENI (which is in jumpbox_public_subnet inside jumpbox_vpc).
        # The new_vpc_private_route_table then directs it to the NAT GW.

        # --- Public VPC TGW Attachment ---
        # Step 12: Attach the jumpbox private subnet to the transit gateway
        # The jumpbox will be able to initiate communication with the range network to access the machines, but the range machines will
        # Not be able to initate communication back to the jumpbox (one-way)
        jumpbox_vpc_tgw_attachment = Ec2TransitGatewayVpcAttachment(
            self,
            f"{range_name}-PublicVpcTgwAttachment",
            subnet_ids=[jumpbox_vpc_private_subnet.id],
            transit_gateway_id=tgw.id,
            vpc_id=jumpbox_vpc.id,
            transit_gateway_default_route_table_association=True,
            transit_gateway_default_route_table_propagation=True,
            tags={"Name": "public-vpc-tgw-attachment"},
        )

        # Step 13: Add Routing to the Transit Gateway
        # Any traffic destined for the internet will route through the transit gateway to the jumpbox private subnet
        # From there the traffic will use the NAT routing table to route to the NAT gateway to access the internet
        tgw_internet_route = Ec2TransitGatewayRoute(  # noqa: F841
            self,
            f"{range_name}-TgwInternetRoute",
            destination_cidr_block="0.0.0.0/0",
            transit_gateway_attachment_id=jumpbox_vpc_tgw_attachment.id,
            transit_gateway_route_table_id=tgw.association_default_route_table_id,
        )

        # Create Range vpcs, subnets, hosts
        for vpc in range_obj.vpcs:

            normalized_vpc_name = normalize_resource_name(vpc.name)

            # Step 14: Create a VPC
            new_vpc = Vpc(
                self,
                f"{range_name}-{normalized_vpc_name}",
                cidr_block=str(vpc.cidr),
                enable_dns_support=True,
                enable_dns_hostnames=True,
                tags={"Name": normalized_vpc_name},
            )

            TerraformOutput(
                self,
                f"{range_name}-{normalized_vpc_name}-resource-id",
                value=new_vpc.id,
                description="Cloud resource id of the vpc created",
                sensitive=True,
            )

            # Step 15: Create security group for access to range hosts
            # Shared security group for all internal resources
            # Every VPC will use the same secrutiy group but security groups are scoped to a single VPC, so they have to be added to each one
            private_vpc_sg = SecurityGroup(
                self,
                f"{range_name}-{normalized_vpc_name}-SharedPrivateSG",
                vpc_id=new_vpc.id,
                tags={"Name": "RangePrivateInternalSecurityGroup"},
            )
            SecurityGroupRule(  # Allow access from the Jumpbox - possibly not needed based on next rule
                self,
                f"{range_name}-{normalized_vpc_name}-RangeAllowAllTrafficFromJumpBox-Rule",
                type="ingress",
                from_port=0,
                to_port=0,
                protocol="-1",
                cidr_blocks=["10.255.99.0/24"],
                security_group_id=private_vpc_sg.id,
            )
            SecurityGroupRule(
                self,
                f"{range_name}-{normalized_vpc_name}-RangeAllowInternalTraffic-Rule",  # Allow all internal subnets to communicate with each other
                type="ingress",
                from_port=0,
                to_port=0,
                protocol="-1",
                cidr_blocks=["0.0.0.0/0"],
                security_group_id=private_vpc_sg.id,
            )
            SecurityGroupRule(
                self,
                f"{range_name}-{normalized_vpc_name}-RangeAllowPrivateOutbound-Rule",
                type="egress",
                from_port=0,
                to_port=0,
                protocol="-1",
                cidr_blocks=["0.0.0.0/0"],
                security_group_id=private_vpc_sg.id,
            )

            current_vpc_subnets: list[Subnet] = []
            # Step 16: Create private subnets with their respecitve EC2 instances
            for subnet in vpc.subnets:

                normalized_subnet_name = normalize_resource_name(subnet.name)

                new_subnet = Subnet(
                    self,
                    f"{range_name}-{normalized_vpc_name}-{normalized_subnet_name}",
                    vpc_id=new_vpc.id,
                    cidr_block=str(subnet.cidr),
                    availability_zone="us-east-1a",
                    tags={"Name": normalized_subnet_name},
                )

                TerraformOutput(
                    self,
                    f"{range_name}-{normalized_vpc_name}-{normalized_subnet_name}-resource-id",
                    value=new_subnet.id,
                    description="Cloud resource id of the subnet created",
                    sensitive=True,
                )

                current_vpc_subnets.append(new_subnet)

                # Create specified instances in the given subnet
                for host in subnet.hosts:
                    ec2_instance = Instance(
                        self,
                        f"{range_name}-{normalized_vpc_name}-{normalized_subnet_name}-{host.hostname}",
                        ami=AWS_OS_MAP[host.os],
                        instance_type=AWS_SPEC_MAP[host.spec],
                        subnet_id=new_subnet.id,
                        vpc_security_group_ids=[private_vpc_sg.id],
                        key_name=key_pair.key_name,  # Use the generated key pair
                        tags={"Name": host.hostname},
                    )

                    TerraformOutput(
                        self,
                        f"{range_name}-{normalized_vpc_name}-{normalized_subnet_name}-{host.hostname}-resource-id",
                        value=ec2_instance.id,
                        description="Cloud resource id of the ec2 instance created",
                        sensitive=True,
                    )
                    TerraformOutput(
                        self,
                        f"{range_name}-{normalized_vpc_name}-{normalized_subnet_name}-{host.hostname}-private-ip",
                        value=ec2_instance.private_ip,
                        description="Cloud private IP address of the ec2 instance created",
                        sensitive=True,
                    )

            # Step 17: Attach  VPC to Transit Gateway
            private_vpc_tgw_attachment = Ec2TransitGatewayVpcAttachment(  # noqa: F841
                self,
                f"{range_name}-{normalized_vpc_name}-PrivateVpcTgwAttachment",
                subnet_ids=[
                    current_vpc_subnets[0].id
                ],  # Attach TGW ENIs to all private subnets
                transit_gateway_id=tgw.id,
                vpc_id=new_vpc.id,
                transit_gateway_default_route_table_association=True,
                transit_gateway_default_route_table_propagation=True,
                tags={"Name": f"{normalized_vpc_name}-private-vpc-tgw-attachment"},
            )

            # Step 18: Create Routing in range VPC (Routes to TGW to access other range VPCs or the internet via the NAT gateway)
            new_vpc_private_route_table = RouteTable(
                self,
                f"{range_name}-{normalized_vpc_name}-PrivateRouteTable",
                vpc_id=new_vpc.id,
                tags={"Name": f"{normalized_vpc_name}-private-route-table"},
            )
            # Default route for range VPC to Transit Gateway
            tgw_route = Route(  # noqa: F841
                self,
                f"{range_name}-{normalized_vpc_name}-PrivateTgwRoute",
                route_table_id=new_vpc_private_route_table.id,
                destination_cidr_block="0.0.0.0/0",  # All traffic goes to TGW
                transit_gateway_id=tgw.id,
            )
            # Associate VPC subnets with Route Table to route traffic to the TGW
            for i, created_subnet in enumerate(current_vpc_subnets):
                RouteTableAssociation(
                    self,
                    f"{range_name}-{normalized_vpc_name}-PrivateSubnetRouteTableAssociation_{i+1}",
                    subnet_id=str(created_subnet.id),
                    route_table_id=new_vpc_private_route_table.id,
                )

            # Step 20: Create Routing in Jumpbox VPC
            # --- Add routes in Jumpbox VPC to reach range VPCs via TGW ---
            # Add route to the Jumpbox VPC's Public route table (for Jumpbox access & NAT Return Traffic)
            Route(
                self,
                f"{range_name}-{normalized_vpc_name}-PublicRtbToPrivateVpcRoute",
                route_table_id=jumpbox_route_table.id,  # Route in the public subnet's RT
                destination_cidr_block=new_vpc.cidr_block,  # Traffic destined to the range VPCs will go through the transit gateway
                transit_gateway_id=tgw.id,
            )
            # Add route to the Jumpbox VPC's NAT route table (for TGW -> Private VPC traffic, though propagation often handles this)
            # This ensures traffic arriving *from* the TGW destined for another private VPC goes back *to* the TGW
            Route(
                self,
                f"{range_name}-{normalized_vpc_name}-PublicVpcTgwSubnetRtbToPrivateVpcRoute",
                route_table_id=nat_route_table.id,  # Route in the TGW attachment subnet's Route Table (jumpbox private subnet)
                destination_cidr_block=new_vpc.cidr_block,  # Traffic destined to the range VPCs will go through the transit gateway
                transit_gateway_id=tgw.id,
            )
