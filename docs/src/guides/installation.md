# 🛠️ Installation

This guide will get OpenLabs running on your local machine using Docker.

> [!IMPORTANT]
> You must have **Git** and **Docker Desktop** (or Docker with Compose) installed.
>
> * [Install Git](https://git-scm.com/downloads)
> * [Install Docker Desktop](https://www.docker.com/products/docker-desktop/)

## 📦 Step 1: Clone the Repository

Open your terminal and run the following command to clone the repository onto your machine.

```bash
git clone https://github.com/OpenLabsHQ/OpenLabs
```

## 🛠️ Step 2: Demo Configuration

Navigate into the new directory. OpenLabs requires a `.env` file for configuration, even if it's empty.

```bash
cd OpenLabs/
touch .env
```

> [!WARNING]
> This quick setup uses **insecure** default values suitable only for local testing. For production, please see our [Configuration](guides/configuration.md) guide.

## 🚀 Step 3: Launch OpenLabs

Run Docker Compose to build and start all the OpenLabs services. 

```bash
docker compose --profile frontend up
```

> [!NOTE]
> The first launch may take several minutes to download the required images. Subsequent launches will be significantly faster.

## ✅ Step 4: Verify Your Installation

Visit: [http://localhost:3000](http://localhost:3000). You should see the OpenLabs homepage.

## 🎉 Success

Congratulations, OpenLabs is now running!

Now you're ready to deploy your first lab. Head back to the [Quick Start Tutorial](../tutorials/quick-start.md) to continue.