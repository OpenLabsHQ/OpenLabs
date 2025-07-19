import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

import dotenv
import pytest
from testcontainers.compose import DockerCompose

from utils import (
    find_git_root,
    get_free_port,
    rotate_docker_compose_test_log_files,
)

# Docker Compose config
COMPOSE_DIR = find_git_root()
COMPOSE_FILES = ["docker-compose.yml", "docker-compose.test.yml"]
COMPOSE_PROFILES = ["frontend"]

API_PORT_VAR_NAME = "API_PORT"
FRONTEND_PORT_VAR_NAME = "FRONTEND_PORT"
FRONTEND_URL_VAR_NAME = "FRONTEND_URL"

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def create_test_output_dir() -> str:
    """Create test output directory `.testing-out`.

    Returns
    -------
        str: Path to test output dir.

    """
    test_output_dir = "./testing-out/"
    if not os.path.exists(test_output_dir):
        os.makedirs(test_output_dir)

    return test_output_dir


@pytest.fixture(scope="session")
def test_env_file() -> Generator[Path, None, None]:
    """Create a test .env file."""
    env_path = Path(f"{COMPOSE_DIR}/.env")
    backup_path = env_path.with_suffix(env_path.suffix + ".bak")
    example_path = Path(f"{COMPOSE_DIR}/.env.example")

    if not example_path.is_file():
        pytest.fail(f"Required example .env file not found: {example_path}")

    # Back up the original .env if it exists
    original_env_existed = env_path.exists()
    if original_env_existed:
        env_path.rename(backup_path)
        logger.info("Backed up existing .env file to: %s.", backup_path)

    # Create the test .env from the example
    new_env_path = shutil.copy(example_path, env_path)

    try:
        yield new_env_path
    finally:
        if original_env_existed:
            backup_path.replace(env_path)
            logger.info("Restored .env file from backup.")
        else:
            # If no backup, cleanup our test .env
            env_path.unlink()
            logger.info("Removed temporary .env file.")


def configure_e2e_test_app(test_env_file: Path) -> None:
    """Configure a .env file for end-to-end testing.

    Args:
        test_env_file: Path to test .env file

    Returns:
        None

    """
    if not test_env_file.is_file():
        pytest.fail("Failed to configure .env file for testing. Env file not found!")

    # Set env variables
    dotenv.set_key(test_env_file, API_PORT_VAR_NAME, str(get_free_port()))
    dotenv.set_key(test_env_file, FRONTEND_PORT_VAR_NAME, str(get_free_port()))


@pytest.fixture(scope="session")
def docker_services(
    create_test_output_dir: str,
    test_env_file: Path,
) -> Generator[DockerCompose, None, None]:
    """Spin up docker compose environment using `docker-compose.yml` in project root."""
    configure_e2e_test_app(test_env_file)

    with DockerCompose(
        context=COMPOSE_DIR,
        compose_file_name=COMPOSE_FILES,
        pull=True,
        build=True,
        wait=False,
        keep_volumes=False,
        profiles=COMPOSE_PROFILES,
    ) as compose:
        logger.info("Docker Compose environment started.")
        try:
            yield compose
        finally:
            logger.info("Saving container logs...")

            timestamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
            log_filename = f"docker_compose_test_{timestamp}.log"
            log_path = os.path.join(create_test_output_dir, log_filename)

            stdout, stderr = compose.get_logs()

            # Save the logs to a file
            with open(log_path, "w", encoding="utf-8") as f:
                f.write("--- STDOUT ---\n")
                f.write(stdout)
                f.write("\n--- STDERR ---\n")
                f.write(stderr)

            logger.info("Container logs saved to: %s", log_path)

            rotate_docker_compose_test_log_files(create_test_output_dir)

    logger.info("Docker Compose environment stopped.")


@pytest.fixture(scope="session")
def app_url(docker_services: DockerCompose, test_env_file: Path) -> str:
    """Wait for the frontend service to be ready and returns its base URL."""
    frontend_url = dotenv.get_key(test_env_file, FRONTEND_URL_VAR_NAME)

    # Wait until the frontend URL is accessible
    logger.info("Waiting for frontend service at %s...", frontend_url)
    docker_services.wait_for(frontend_url)
    logger.info("Frontend service is ready.")

    return frontend_url
