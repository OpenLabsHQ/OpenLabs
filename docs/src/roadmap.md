# 🗺️ Roadmap

Our vision for OpenLabs is ambitious. The table below outlines the major outcomes we are focused on delivering. It's a living document that will evolve based on project needs and community feedback.

**Status:** Shows the current stage of a feature.
* `🧪 Exploring`: We are researching and designing the feature.
* `🗓️ Planned`: The feature is designed and is in our near-term backlog.
* `🏗️ In Progress`: The feature is in active development.

**Timeline:** Provides a general estimate. As an open-source project, these are targets, not promises.

| Feature/Outcome                | Description                                                                                                                   | Status          | Estimated Timeline   |
| :----------------------------- | :---------------------------------------------------------------------------------------------------------------------------- | :-------------- | :------------------- |
| [**Live Environment Management**](https://github.com/OpenLabsHQ/OpenLabs/milestone/1) | Dynamically add/remove hosts, power them on/off, and manage firewall rules in a deployed Range without a full redeploy.       | 🏗️ In Progress      | Q3 2025              |
| [**Lab Snapshots & Cloning**](https://github.com/OpenLabsHQ/OpenLabs/milestone/2) | Save the complete state of a running host or an entire Range. Deploy perfect, pre-configured clones from a snapshot.           | 🗓️ Planned | Q3 2025              |
| [**Automated Range Cleanup**](https://github.com/OpenLabsHQ/OpenLabs/milestone/3) | Set expiration timers to automatically shut down or destroy deployed Ranges, helping reduce cloud costs. | 🗓️ Planned | Q3 2025 |
| [**Azure Cloud Provider**](https://github.com/OpenLabsHQ/OpenLabs/milestone/5) | Define your lab once and deploy it to Microsoft Azure, in addition to our existing AWS support.                               | 🗓️ Planned      | Q3 2025    |
| [**Workspaces for Teams**](https://github.com/OpenLabsHQ/OpenLabs/milestone/4) | Create shared workspaces for teams to collaborate on Blueprints and manage deployed Ranges with role-based permissions.         | 🧪 Exploring    | Q3 2025               |
| **Custom & Pre-Built Images** | Use Packer integration to build your own "golden images" or use official pre-built ones.                  | 🧪 Exploring    | Q4 2025             |
| **Integrated Remote Access** | Securely connect to your lab hosts via an auto-configured VPN and in-browser terminal/VNC access (via Apache Guacamole).      | 🧪 Exploring      | Q4 2025              |
| **Automated Host Configuration** | Attach Ansible playbooks or roles to your Blueprints to automatically provision software on your hosts after they are deployed. | 🧪 Exploring  | Q4 2025 - Q1 2026             |

> Have an idea or want to provide feedback on our direction? We'd love to hear from you! Please **[start a discussion on GitHub](https://github.com/OpenLabsHQ/OpenLabs/discussions)**.