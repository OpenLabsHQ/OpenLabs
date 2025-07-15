<h1 align="center">OpenLabs API</h1>

<p align="center">
<a href="https://github.com/OpenLabsHQ/OpenLabs"><img alt="Latest version" src="https://img.shields.io/github/v/release/OpenLabsHQ/OpenLabs"></a>
<a href="https://github.com/psf/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
<a href="https://github.com/astral-sh/ruff"><img alt="Linting: ruff" src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json"></a>
<a href="https://mypy-lang.org/"><img alt="Checked with mypy" src="https://www.mypy-lang.org/static/mypy_badge.svg"></a>
</p>


## Table of Contents

1. [Quickstart](#quickstart)
2. [Project Structure](#project-structure)
3. [Environment Setup](#environment-setup)
4. [Tests](#tests)
5. [Debugging](#debugging)
6. [Workflows](#workflows)
7. [Contributing](/CONTRIBUTING.md)
8. [License](/LICENSE)


## Quickstart

Clone the repo:

```bash
git clone https://github.com/OpenLabsHQ/OpenLabs.git
```

Copy the ENV example:

```bash
cd OpenLabs/
cp .env.example .env
```

Start the docker compose:

```bash
docker compose up --build
```

Congrats! It's working! 🎉 
* API Documentation: [http://localhost:8000/docs](http://127.0.0.1:8000/docs)
* OpenLabs Docs: [https://docs.openlabs.sh/](https://docs.openlabs.sh/)


## Project Structure

```txt
src/
├── app
│   ├── api                 # API routes
│   ├── core
│   │   ├── auth
│   │   ├── cdktf           # Terraform CDKTF logic
│   │   │   ├── hosts   
│   │   │   ├── ranges
│   │   │   ├── stacks
│   │   │   ├── subnets
│   │   │   └── vpcs
│   │   └── db              # Database configuration
│   ├── crud
│   ├── enums               # User options
│   ├── logs
│   ├── middlewares
│   ├── models              # ORM models
│   ├── schemas             # API/Pydantic schemas
│   ├── utils
│   ├── validators
│   └── main.py             # Application entry point
│
└── scripts                 # Setup scripts
```


## Environment Setup

Create environment:

```bash
python3.12 -m venv venv
```

Activate environment:

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install --upgrade pip
pip install -r requirements.txt
pip install -r dev-requirements.txt
```

## Tests

Run tests:

```bash
# Unit tests
pytest -m unit

# Integration tests (no deployments)
pytest -m "integration and not deploy"

# Configure provider credentials
cp .env.tests.example .env.tests

# Provider specific tests
pytest -m aws
```

> See `marks` defined in `pyproject.toml` for more options.

Code coverage:

```bash
open htmlcov/index.html
```

Test session logs:

```bash
# Pytest logs (fixture setup)
pytest_run.log

# Integration tests docker log
docker_compose_test_*.log
```

All test related logs are stored in `.testing-out/`.


### Test Organization

All tests are located in `tests/` with each subdirectory mirroring `src/app/`:

* `unit` - Unit tests.
* `integration` - Integration tests (docker compose).
* `common` - Tests shared by unit and integration test suites.


## Debugging

To debug with the docker compose:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

The app will only be started once you run the debugger in VScode using the `Python: Remote Attach to OpenLabs API` profile.

## Workflows

### Quality Gates

* `api-black.yml` - Runs the Black code formatter in check mode to verify code formatting.
* `api-ruff.yml` - Runs the Ruff linter to check for code quality issues.
* `api-mypy.yml` - Performs static type checking with MyPy.
* `api-unit_tests.yml` - Runs all unit tests.
* `api-integration_tests.yml` Runs integration tests that do **not** deploy live infrastructure.
* `api-aws_tests.yml` - Run all AWS specific tests including live deploy tests.

### Release Management

- `check_pr_labels.yml` - Checks for properly labeled PRs required by *auto_release.yml*.
- `auto_release.yml` - Creates GitHub tagged releases based on the tag of the PR. 
