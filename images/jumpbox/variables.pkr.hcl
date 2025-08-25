variable "image_name_prefix" {
  type        = string
  default     = "openlabs-jumpbox"
  description = "Prefix for the name of the created image/AMI."
}

# AWS Variables
variable "aws_image_build_region" {
  type        = string
  default     = "us-east-1"
  description = "The AWS region where the AMI will be built."
}

variable "aws_instance_type" {
  type        = string
  default     = "t3.micro"
  description = "The EC2 instance type for building."
}
