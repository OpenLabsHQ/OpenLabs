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

## 🛠️ Step 2: Configure the App

Navigate into the new directory. OpenLabs requires a `.env` file for configuration.

```bash
cd OpenLabs/
cp .env.example .env

# Set credentials
nano .env
```

## 🚀 Step 3: Launch OpenLabs

Run Docker Compose to build and start all the OpenLabs services. 

```bash
docker compose --profile frontend up -d
```

> [!NOTE]
> The first launch may take several minutes to download the required images. Subsequent launches will be significantly faster.

## ✅ Step 4: Verify Your Installation

Visit: [http://localhost:3000](http://localhost:3000). You should see the OpenLabs homepage.

## 🎉 Success

Congratulations, OpenLabs is now running!

Now you're ready to deploy your first lab. Head back to the [Deploy Your First Range](../tutorials/deploy-your-first-range.md) to continue.