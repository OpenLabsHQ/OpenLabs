import logging
from datetime import UTC, datetime
from typing import Any, List, Tuple

import boto3
from botocore.exceptions import ClientError

from src.app.models.secret_model import SecretModel
from src.app.schemas.message_schema import AWSUpdateSecretMessageSchema, MessageSchema
from src.app.schemas.secret_schema import AWSSecrets
from src.app.utils.crypto import encrypt_with_public_key

from .base_creds import AbstractBaseCreds

# Configure logging
logger = logging.getLogger(__name__)


class AWSCreds(AbstractBaseCreds):
    """Credential verification for AWS."""

    credentials: AWSSecrets

    def __init__(self, credentials: dict[str, Any]) -> None:
        """Initialize AWS credentials verification object."""
        self.credentials = AWSSecrets.model_validate(credentials)

    def update_user_secrets(
        self, secrets: SecretModel, current_user_public_key: str
    ) -> MessageSchema:
        """Update user AWS secrets in user record."""
        # Convert to dictionary for encryption
        aws_data = {
            "aws_access_key": self.credentials.aws_access_key,
            "aws_secret_key": self.credentials.aws_secret_key,
        }

        # Encrypt with the user's public key
        encrypted_data = encrypt_with_public_key(aws_data, current_user_public_key)

        # Update the secrets with encrypted values
        secrets.aws_access_key = encrypted_data["aws_access_key"]
        secrets.aws_secret_key = encrypted_data["aws_secret_key"]
        secrets.aws_created_at = datetime.now(UTC)

        return AWSUpdateSecretMessageSchema(
            message="AWS credentials updated successfully"
        )

    def verify_creds(self) -> Tuple[bool, MessageSchema]:
        """Verify credentials authenticate to an AWS account."""
        try:
            # --- Step 1: Basic Authentication with STS ---
            client = boto3.client(
                "sts",
                aws_access_key_id=self.credentials.aws_access_key,
                aws_secret_access_key=self.credentials.aws_secret_key,
            )
            caller_identity = (
                client.get_caller_identity()
            )  # will raise an error if not valid
            caller_arn = caller_identity["Arn"]
            logger.info(
                "AWS credentials successfully authenticated for ARN: %s", caller_arn
            )

            # --- Step 2: Simulate permissions for a sample of minimum critical actions ---
            iam_client = boto3.client(
                "iam",
                aws_access_key_id=self.credentials.aws_access_key,
                aws_secret_access_key=self.credentials.aws_secret_key,
            )

            actions_to_test = [
                # For Instance
                "ec2:RunInstances",
                "ec2:TerminateInstances",
                "ec2:DescribeInstances",
                # For Vpc
                "ec2:CreateVpc",
                "ec2:DeleteVpc",
                "ec2:DescribeVpcs",
                # For Subnet
                "ec2:CreateSubnet",
                "ec2:DeleteSubnet",
                "ec2:DescribeSubnets",
                # For InternetGateway
                "ec2:CreateInternetGateway",
                "ec2:DeleteInternetGateway",
                "ec2:AttachInternetGateway",
                "ec2:DetachInternetGateway",
                # For Eip and NatGateway
                "ec2:AllocateAddress",  # Create EIP
                "ec2:ReleaseAddress",  # Delete EIP
                "ec2:AssociateAddress",
                "ec2:CreateNatGateway",
                "ec2:DeleteNatGateway",
                # For KeyPair
                "ec2:CreateKeyPair",
                "ec2:DeleteKeyPair",
                # For SecurityGroup and SecurityGroupRule
                "ec2:CreateSecurityGroup",
                "ec2:DeleteSecurityGroup",
                "ec2:AuthorizeSecurityGroupIngress",
                "ec2:RevokeSecurityGroupIngress",
                "ec2:AuthorizeSecurityGroupEgress",
                "ec2:RevokeSecurityGroupEgress",
                # For RouteTable, Route, and RouteTableAssociation
                "ec2:CreateRouteTable",
                "ec2:DeleteRouteTable",
                "ec2:CreateRoute",
                "ec2:DeleteRoute",
                "ec2:AssociateRouteTable",
                "ec2:DisassociateRouteTable",
                # For Transit Gateway ---
                "ec2:CreateTransitGateway",
                "ec2:DeleteTransitGateway",
                "ec2:CreateTransitGatewayVpcAttachment",
                "ec2:DeleteTransitGatewayVpcAttachment",
                "ec2:CreateTransitGatewayRoute",
                "ec2:DeleteTransitGatewayRoute",
                "ec2:DescribeTransitGateways",
                "ec2:DescribeTransitGatewayVpcAttachments",
            ]

            simulation_results = iam_client.simulate_principal_policy(
                PolicySourceArn=caller_arn, ActionNames=actions_to_test
            )

            # --- Step 3: Evaluate the simulation results ---
            denied_actions: List[str] = []
            for result in simulation_results["EvaluationResults"]:
                if result["EvalDecision"] != "allowed":
                    denied_actions.append(result["EvalActionName"])

            if not denied_actions:
                logger.info(
                    "All simulated actions were allowed for ARN: %s", caller_arn
                )
                return (
                    True,
                    MessageSchema(
                        message="AWS credentials authenticated and all required permissions are present."
                    ),
                )

            error_message = f"Authentication succeeded, but the user/group is missing required permissions. The following actions were denied: {', '.join(denied_actions)}"
            logger.error(error_message)
            return (
                False,
                MessageSchema(
                    message=f"Insufficient permissions for your AWS account user/group. Please ensure the following permissions are added: {', '.join(denied_actions)}"
                ),
            )
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code in ("InvalidClientTokenId", "SignatureDoesNotMatch"):
                message = "AWS credentials could not be authenticated. Please ensure you are providing credentials that are linked to a valid AWS account."
            elif error_code == "AccessDenied":
                message = "AWS credentials are valid, but lack permissions to perform the permissions verification. Please ensure you give your AWS account user/group has the iam:SimulatePrincipalPolicy permission attached to a policy."
            else:
                message = e.response["Error"]["Message"]
            logger.error("AWS verification failed: %s", message)
            return (
                False,
                MessageSchema(message=message),
            )
