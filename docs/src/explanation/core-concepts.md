# 🧠 Core Concepts

This page explains the fundamental building blocks of the platform.

At its heart, the OpenLabs lifecycle is simple: you define a **Blueprint**, deploy it to create a live **Range**, and can later save that Range as a **Snapshot**.

## Main Components

These are the three primary objects you will interact with in OpenLabs.

* 🏗️ **Blueprint**: The YAML file that acts as a recipe for your lab. It defines every part of your environment: VPCs, subnets, hosts, and their configurations. A Blueprint doesn't represent any live cloud resources and doesn't cost anything.

* ☁️ **Range**: The live, running version of a Blueprint. When you deploy a Blueprint, OpenLabs creates a Range, which consists of all the actual cloud resources (VMs, networks, etc.). This is the environment you interact with, and it is what incurs costs from your cloud provider.

* 📸 **Snapshot**: A point-in-time backup of a Range. It saves the state of all hosts and the network configuration. You can use a Snapshot to restore a lab to a previous state or to deploy new, identical clones of the snapshotted range.

Below is a visualization of how these relate to each other:

<img src="../assets/images/3-openlabs_state_flow.drawio.svg" style="width: 100%; height: auto; display: block; margin-left: auto; margin-right: auto;" alt="Screenshot of user settings button location.">

## Lab Hierarchy

Every lab you build follows a logical network hierarchy. This structure helps you organize even the most complex environments.

* **Range**: The top-level container for your entire deployed lab.

* **VPC**: (Virtual Private Cloud) An isolated network within your Range. A Range can have multiple VPCs.

* **Subnet**: A subdivision of a VPC's IP address range where hosts live.

* **Host**: An individual virtual machine (VM) running within a Subnet.