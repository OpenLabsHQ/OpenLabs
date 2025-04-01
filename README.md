# API

## Table of Contents

1. [Developer Quickstart](#developer-quickstart)
2. [Tests](#tests)
3. [Project Structure](#project-structure)
4. [VScode Extensions](#vscode-extensions)
5. [Debugging](#debugging)
6. [Workflows](#workflows)
7. [Contributing](/CONTRIBUTING.md)
8. [License](/LICENSE)

## Developer Quickstart

Welcome to the project! Follow these steps to get the service up and running for development.

### 1. Setup Configuration

Create a `.env` file in the project root. This file configures both FastAPI and Docker.

```bash
cp .env.example .env
```

---

### 2. Choose Your Run Method

- **[Run with Docker](#run-with-docker)** *(Recommended for most users)*
- **[Run Locally (Without Docker)](#run-locally-without-docker)** *(For local development setups)*

## Run with Docker

**Prerequisites**
- Install [Docker](https://docs.docker.com/engine/install/) and `docker compose`.

**Steps**

1) Build and Run Containers:

    ```bash
    docker compose up
    ```
    > **Note:** If you get a `KeyError: 'ContainerConfig'` error, run `docker container prune -f` to remove stopped containers.

2) Congrats! It's working! 🎉

    **API:**
    - API Documentation: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)  
    - Health Check Endpoint: [http://127.0.0.1:8000/api/v1/health/ping](http://127.0.0.1:8000/api/v1/health/ping)

    **Database:**
    - PostgreSQL is available locally on port `5432` (configured via `POSTGRES_DEBUG_PORT`).
    - Connect using:

      ```bash
      psql -h localhost -p 5432 -U postgres -d openlabsx
      ```

*See [Python Environment Setup](#python-environment-setup) to configure your virtual environment.*

## Run Locally (Without Docker)

**Prerequisites**
- Install and configure [PostgreSQL](https://coding-boot-camp.github.io/full-stack/postgresql/postgresql-installation-guide#install-postgresql-server).

**Steps**

1. [Setup your Python Environment](#python-environment-setup)

2. Start the API Server:

    ```bash
    fastapi dev src/app/main.py
    ```

3. Congrats! It's working! 🎉

    - API Documentation: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
    - Health Check Endpoint: [http://127.0.0.1:8000/api/v1/health/ping](http://127.0.0.1:8000/api/v1/health/ping)

## Python Environment Setup

**Prerequisites**
- Install [Python 3.12+](https://www.python.org/downloads/).

**Steps**

1. Create Virtual Environment:

    ```bash
    python3.12 -m venv venv
    ```

2. Activate Virtual Environment:

    ```bash
    source venv/bin/activate
    ```

3. Install Dependencies:

    ```bash
    pip install --upgrade pip
    pip install -r requirements.txt
    pip install -r dev-requirements.txt
    ```

4. Run Pre-Commit Hook (Verify Setup):

    ```bash
    pre-commit run --all-files
    ```

## Tests

### Run Tests

```bash
# All tests
pytest

# Unit tests
pytest tests/unit/

# Integration Tests
pytest tests/integration/
```

### Code Coverage Report

```bash
pytest
open htmlcov/index.html
```

### Test Organization

All tests are located in `tests/`. The structure of the `tests/` directory mirrors the `src/app/` directory structure.

## Project Structure

```
src/
└── app
    ├── api
    │   └── v1                   # API Version 1 routes (/v1)
    |       |                    # ------------------------- #
    │       ├── auth.py          # /auth routes
    │       ├── health.py        # /health routes
    │       ├── ranges.py        # /ranges routes
    │       ├── templates.py     # /templates routes
    │       └── users.py         # /users routes
    |
    ├── core                     # Core Application Logic
    |   |                        # ---------------------- #
    │   ├── auth/                # Authentication utilities
    │   │   └── auth.py
    │   ├── cdktf/               # CDKTF Libraries
    │   │   └── aws/             # AWS provider configuration
    │   ├── config.py            # Application settings
    │   ├── db                   # Database configuration
    │   │   └── database.py
    │   ├── logger.py            # Shared logger utility
    │   └── setup.py             # Application setup logic
    | 
    ├── crud                     # Database CRUD operations
    │   ├── crud_host_templates.py
    │   ├── crud_range_templates.py
    │   ├── crud_subnet_templates.py
    │   ├── crud_users.py
    │   └── crud_vpc_templates.py
    |
    ├── enums                    # Enums (Constants)
    |   |                        # ---------------- #
    │   ├── operating_systems.py # OS configurations
    │   ├── providers.py         # Defined cloud providers
    │   └── specs.py             # Preset VM hardware configurations
    |
    ├── models                   # Database Models
    │   ├── secret_model.py        # Encrypted cloud provider credentials (AWS, Azure)
    │   ├── template_base_model.py
    │   ├── template_host_model.py
    │   ├── template_range_model.py
    │   ├── template_subnet_model.py
    │   ├── template_vpc_model.py
    │   └── user_model.py
    |
    ├── schemas                  # API Schema (Objects)
    |   |                        # ------------------ #
    │   ├── secret_schema.py      # Cloud provider credential schemas
    │   ├── template_host_schema.py
    │   ├── template_range_schema.py
    │   ├── template_subnet_schema.py
    │   ├── template_vpc_schema.py
    │   └── user_schema.py
    |
    ├── utils                    # Utility Functions
    │   ├── cdktf_utils.py       # CDKTF configuration utilities
    │   └── crypto.py            # Cryptography utilities for encrypting cloud provider credentials
    |
    ├── validators               # Data Validation
    |   |                        # --------------- #
    │   ├── id.py                # ID validation
    │   └── network.py           # Networking config input validation
    |
    └── main.py                  # Main App Entry Point
```

## VScode Extensions

This is a list of extensions that this project was configured to work with. It has only been tested on VScode.

**Extensions:**
- [Black Formatter](https://marketplace.visualstudio.com/items?itemName=ms-python.black-formatter)
- [Mypy Type Checker](https://marketplace.visualstudio.com/items?itemName=ms-python.mypy-type-checker)
- [Pylance](https://marketplace.visualstudio.com/items?itemName=ms-python.vscode-pylance)
- [Python Debugger](https://marketplace.visualstudio.com/items?itemName=ms-python.debugpy)
- [Ruff](https://marketplace.visualstudio.com/items?itemName=charliermarsh.ruff)

### Black Formatter

You can configure Black to format on save (`Ctrl`+`S`) with the following configuration in **Preferences: Open User Settings (JSON)** (`Ctrl`+`Shift`+`P`).

```
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter",
    "editor.formatOnSave": true
  }
```

## Debugging

To debug with the python debugger extension, use the `docker-compose.dev.yaml` file.

```bash
docker compose -f docker-compose.dev.yml up
```

The app will only be started once you run the debugger in VScode.

All changes made to code in your local directory will be applied to the container app and should reload automatically.

## Workflows

### Code Quality and Testing

#### `black.yml`

Runs the Black code formatter in check mode to verify code formatting. The workflow will fail if formatting is needed.

#### `ruff.yml`

Runs the Ruff linter to check for code quality issues.

#### `mypy.yml`

Performs static type checking with MyPy.

#### `unit_tests.yml`

Runs all unit tests located in `tests/unit/`.

#### `integration_tests.yml`

Runs integration tests located in `tests/integration/`.

### Release Management

#### `check_pr_labels.yml`

This workflow checks if you correctly labeled your PR for the `auto_release.yml` workflow to create a proper release. *This workflow will recheck when new labels are added to the PR.*

**Setup:** To setup this workflow, you just need a `CONTRIBUTING.md` file in the root of your project. At minimum it should have a section called `No semver label!` ([Link to example](https://github.com/alexchristy/PyOPN/blob/main/CONTRIBUTING.md#no-semver-label)). The workflow will automatically link this section when it fails so user's can fix their PRs. Feel free to copy the example.

#### `auto_release.yml`

This workflow automatically creates GitHub tagged releases based on the tag of the PR. 

**Setup:**

1) Install the [Auto release tool](https://intuit.github.io/auto/docs) ([Latest release](https://github.com/intuit/auto/releases))

2) Navigate to the repository

    ```bash
    cd /path/to/repo/API/
    ```

3) Initialize Auto

    For this step the choose `Git Tag` as the *package manager plugin*. Fill in the rest of the information relevant to the repo and keep **all** default values. 

    When prompted for a *Github PAT*, go to the next step.

    ```bash
    auto init
    ```

4) Create repository tags

    This will allow you to tag your PRs and control the semantic version changes.

    ```bash
    auto create-labels
    ```

5) Create a GitHub App

    ***Note:** OpenLabs already has the `auto-release-app` installed. Skip to step 7.*

    This allows us to enforce branch protection rules while allowing the Auto release tool to bypass the protections when running automated workflows. (Source: [Comment Link](https://github.com/orgs/community/discussions/13836#discussioncomment-8535364))
    
    Link: [Making authenticated API requests with a GitHub App in a GitHub Actions workflow](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/making-authenticated-api-requests-with-a-github-app-in-a-github-actions-workflow)

6) Configure the app with the following permissions

    * Actions (read/write)
    * Administration (read/write)
    * Contents (read/write)

7) Update the ruleset bypass list to include the GitHub App

8) Add GitHub app variables and secrets

    **Secrets:**
    * `AUTO_RELEASE_APP_PRIVATE_KEY`
    * `AUTO_RELEASE_APP_ID`
