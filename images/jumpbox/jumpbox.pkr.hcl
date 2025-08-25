packer {
  required_plugins {
    amazon = {
      version = ">= 1.2.1"
      source  = "github.com/hashicorp/amazon"
    }
  }
}

build {
  name = "openlabs-jumpbox-build"
  sources = [
    "source.amazon-ebs.jumpbox",
  ]

  # Setup environment for Ansible
  provisioner "shell" {
    inline = [
      "echo 'Waiting for cloud-init to finish...'",
      "sudo cloud-init status --wait",

      "echo 'Updating packages to the latest version...'",
      "sudo apt-get update -y",
      "sudo DEBIAN_FRONTEND=noninteractive apt-get upgrade -y",

      "echo 'Installing Ansible...'",
      "sudo DEBIAN_FRONTEND=noninteractive apt-get install -y ansible",

      "echo 'Rebooting the instance to apply updates...'",
      "sudo reboot"
    ]
  }

  # Configure with Ansible
  provisioner "ansible-local" {
    playbook_dir  = "."
    playbook_file = "./playbook.yml"
  }
}
