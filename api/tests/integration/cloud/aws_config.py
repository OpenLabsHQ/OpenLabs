import pytest

# --- IAM ---
SUCCESS_POLICY = {
    "Version": "2012-10-17",
    "Statement": [
        {"Effect": "Allow", "Action": "iam:SimulatePrincipalPolicy", "Resource": "*"},
        {"Effect": "Allow", "Action": "ec2:*", "Resource": "*"},
    ],
}

NO_SIMULATE_POLICY = {
    "Version": "2012-10-17",
    "Statement": [{"Effect": "Allow", "Action": "ec2:*", "Resource": "*"}],
}

INSUFFICIENT_EC2_POLICY = {
    "Version": "2012-10-17",
    "Statement": [
        {"Effect": "Allow", "Action": "iam:SimulatePrincipalPolicy", "Resource": "*"},
        {
            "Effect": "Allow",
            "Action": [
                "ec2:DescribeInstances",
                "ec2:DescribeVpcs",
                "ec2:DescribeSubnets",
            ],
            "Resource": "*",
        },
    ],
}

VERIFY_CREDS_TEST_CASES = [
    pytest.param(
        SUCCESS_POLICY,
        True,
        "permissions are present",
        id="success-all-permissions",
        marks=pytest.mark.aws,
    ),
    pytest.param(
        NO_SIMULATE_POLICY,
        False,
        "iam:simulateprincipalpolicy",
        id="failure-no-simulate-permission",
        marks=pytest.mark.aws,
    ),
    pytest.param(
        INSUFFICIENT_EC2_POLICY,
        False,
        "insufficient permissions",
        id="failure-insufficient-ec2-permissions",
        marks=pytest.mark.aws,
    ),
]
