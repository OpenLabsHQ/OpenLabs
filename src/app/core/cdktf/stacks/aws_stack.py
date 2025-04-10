from ipaddress import IPv4Network

from cdktf import TerraformOutput
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
from ....schemas.template_range_schema import TemplateRangeSchema
from .base_stack import AbstractBaseStack


class AWSStack(AbstractBaseStack):
    """Stack for generating terraform for AWS."""

    def build_resources(
        self,
        template_range: TemplateRangeSchema,
        region: OpenLabsRegion,
        cdktf_id: str,
        range_name: str,
    ) -> None:
        """Initialize AWS terraform stack.

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
        AwsProvider(
            self,
            "AWS",
            region=AWS_REGION_MAP[region],
        )

        # Step 5: Create the key access to all instances provisioned on AWS
        key_pair = KeyPair(
            self,
            f"{range_name}-JumpBoxKeyPair",
            key_name=f"{range_name}-cdktf-key",
            public_key="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIH8URIMqVKb6EAK4O+E+9g8df1uvcOfpvPFl7sQrX7KM email@example.com",  # NOTE: Hardcoded key, will need a way to dynamically add a key to user instances
            tags={"Name": "cdktf-public-key"},
        )

        jumpbox_vpc = Vpc(
            self,
            f"{range_name}-JumpBoxVPC",
            cidr_block="10.255.0.0/16",  # TODO: Dynamically create a cidr block that does not exist with any of the vpc cidr blocks in the template
            enable_dns_support=True,
            enable_dns_hostnames=True,
            tags={"Name": "JumpBoxVPC"},
        )

        # Function to derive a subnet CIDR from the VPC CIDR
        def modify_cidr(vpc_cidr: str, new_third_octet: int) -> str:
            ip_part, prefix = vpc_cidr.split("/")
            octets = ip_part.split(".")
            octets[2] = str(new_third_octet)  # Change the third octet
            octets[3] = "0"  # Explicitly set the fourth octet to 0
            return f"{'.'.join(octets)}/24"  # Convert back to CIDR

        # Generate the new subnet CIDR with third octet = 99
        public_subnet_cidr = modify_cidr(str(jumpbox_vpc.cidr_block), 99)

        public_subnet = Subnet(
            self,
            f"{range_name}-JumpBoxPublicSubnet",
            vpc_id=jumpbox_vpc.id,
            cidr_block=public_subnet_cidr,
            availability_zone="us-east-1a",
            map_public_ip_on_launch=True,
            tags={"Name": "JumpBoxPublicSubnet"},
        )

        # Step 3: Create an Internet Gateway for Public Subnet
        igw = InternetGateway(
            self,
            f"{range_name}-RangeInternetGateway",
            vpc_id=jumpbox_vpc.id,
            tags={"Name": "RangeInternetGateway"},
        )

        # Step 4: Create a NAT Gateway for internal network with EIP
        # Elastic IP for NAT Gateway
        eip = Eip(self, f"{range_name}-RangeNatEIP", tags={"Name": "RangeNatEIP"})

        nat_gateway = NatGateway(
            self,
            f"{range_name}-RangeNatGateway",
            subnet_id=public_subnet.id,  # NAT must be in a public subnet
            allocation_id=eip.id,
            tags={"Name": "RangeNatGateway"},
        )

        jumpbox_route_table = RouteTable(
            self,
            f"{range_name}-JumpBoxRouteTable",
            vpc_id=jumpbox_vpc.id,
            tags={"Name": "RangePublicRouteTable"},
        )

        Route(
            self,
            f"{range_name}-RangePublicInternetRoute",
            route_table_id=jumpbox_route_table.id,
            destination_cidr_block="0.0.0.0/0",  # Allow internet access
            gateway_id=igw.id,
        )

        RouteTableAssociation(
            self,
            f"{range_name}-RangePublicRouteAssociation",
            subnet_id=public_subnet.id,
            route_table_id=jumpbox_route_table.id,
        )

        # Step 8: Create Security Group and Rules for Jump Box (only allow SSH directly into jump box, for now)
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

        # Step 11: Create Jump Box
        jumpbox = Instance(
            self,
            f"{range_name}-JumpBoxInstance",
            ami="ami-014f7ab33242ea43c",  # Amazon Ubuntu 20.04 AMI
            instance_type="t2.micro",
            subnet_id=public_subnet.id,
            vpc_security_group_ids=[jumpbox_sg.id],
            associate_public_ip_address=True,  # Ensures public IP is assigned
            key_name=key_pair.key_name,  # Use the generated key pair
            tags={"Name": f"{range_name}-JumpBox"},
        )

        all_internal_cidrs: list[IPv4Network] = []
        host_ips: list[str] = []
        vpc_ids: list[str] = []
        subnet_ids: list[str] = []
        host_ids: list[str] = []

        # Step 7: Create a Route Table for intenral network (Using NAT)
        private_route_table = RouteTable(
            self,
            f"{range_name}-RangePrivateRouteTable",
            vpc_id=jumpbox_vpc.id,
            tags={"Name": "RangePrivateRouteTable"},
        )
        Route(
            self,
            f"{range_name}-RangePrivateNatRoute",
            route_table_id=private_route_table.id,
            destination_cidr_block="0.0.0.0/0",  # Allow internet access
            nat_gateway_id=nat_gateway.id,  # Route through NAT Gateway
        )

        # Shared security group for all internal resources
        shared_private_sg = SecurityGroup(
            self,
            f"{range_name}-SharedPrivateSG",
            vpc_id=jumpbox_vpc.id,
            tags={"Name": "RangePrivateInternalSecurityGroup"},
        )

        SecurityGroupRule(
            self,
            f"{range_name}-RangeAllowAllTrafficFromJumpBox-Rule",
            type="ingress",
            from_port=0,
            to_port=0,
            protocol="-1",
            security_group_id=shared_private_sg.id,
            source_security_group_id=jumpbox_sg.id,  # Allow all traffic from Jump Box
        )

        SecurityGroupRule(
            self,
            f"{range_name}-RangeAllowInternalTraffic-Rule",  # Allow all internal subnets to communicate with each other
            type="ingress",
            from_port=0,
            to_port=0,
            protocol="-1",
            cidr_blocks=["0.0.0.0/0"],
            security_group_id=shared_private_sg.id,
        )

        SecurityGroupRule(
            self,
            f"{range_name}-RangeAllowPrivateOutbound-Rule",
            type="egress",
            from_port=0,
            to_port=0,
            protocol="-1",
            cidr_blocks=["0.0.0.0/0"],
            security_group_id=shared_private_sg.id,
        )

        for vpc in template_range.vpcs:

            # Step 1: Create a VPC
            new_vpc = Vpc(
                self,
                f"{range_name}-{vpc.name}",
                cidr_block=str(vpc.cidr),
                enable_dns_support=True,
                enable_dns_hostnames=True,
                tags={"Name": vpc.name},
            )
            vpc_ids.append(new_vpc.id)

            # Step 12: Create private subnets with their respecitve EC2 instances
            for subnet in vpc.subnets:
                new_subnet = Subnet(
                    self,
                    f"{range_name}-{vpc.name}-{subnet.name}",
                    vpc_id=new_vpc.id,
                    cidr_block=str(subnet.cidr),
                    availability_zone="us-east-1a",
                    tags={"Name": subnet.name},
                )

                subnet_ids.append(new_subnet.id)
                all_internal_cidrs.append(subnet.cidr)

                RouteTableAssociation(
                    self,
                    f"{range_name}-{vpc.name}-{subnet.name}-RouteAssociation",
                    subnet_id=new_subnet.id,
                    route_table_id=private_route_table.id,
                )
                # Create specified instances in the given subnet
                for host in subnet.hosts:
                    ec2_instance = Instance(
                        self,
                        f"{range_name}-{vpc.name}-{subnet.name}-{host.hostname}",
                        # WIll need to grab from update OpenLabsRange object
                        ami=AWS_OS_MAP[host.os],
                        instance_type=AWS_SPEC_MAP[host.spec],
                        subnet_id=new_subnet.id,
                        vpc_security_group_ids=[shared_private_sg.id],
                        key_name=key_pair.key_name,  # Use the generated key pair
                        tags={"Name": host.hostname},
                    )
                    host_ids.append(ec2_instance.id)
                    host_ips.append(ec2_instance.private_ip)

        TerraformOutput(self, "jumpbox_public_ip", value=jumpbox.public_ip)
        TerraformOutput(self, "host_private_ips", value=host_ips)
        TerraformOutput(self, "vpc_ids", value=vpc_ids)
        TerraformOutput(self, "subnet_ids", value=subnet_ids)
        TerraformOutput(self, "host_ids", value=host_ids)
