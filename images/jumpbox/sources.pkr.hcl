# AWS Source AMI data lookup
data "amazon-ami" "ubuntu_noble" {
  most_recent = true
  owners      = ["099720109477"] # Canonical
  filters = {
    name                = "ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"
    virtualization-type = "hvm"
    architecture        = "x86_64"
  }
}

# AWS Source Builder
source "amazon-ebs" "jumpbox" {
  region        = var.aws_image_build_region
  instance_type = var.aws_instance_type
  ssh_username  = "ubuntu"
  source_ami    = data.amazon-ami.ubuntu_noble.id
  ami_name      = "${var.image_name_prefix}-aws-{{timestamp}}"
  ami_groups	= ["all"] # Public

  # Overwrite old image if it exists
  force_deregister      = true
  force_delete_snapshot = true

  tags = {
    Name        = "${var.image_name_prefix}-aws"
    BaseOS      = "Ubuntu 24.04"
    Project     = "OpenLabs"
  }
}
