import asyncio
import json
import logging
import os
import shutil
import uuid
from pathlib import Path
from typing import Callable
from unittest.mock import AsyncMock, MagicMock

import aiofiles as aiofiles_mock_target
import aiofiles.os as aio_os_mock_target
import pytest

from src.app.core.cdktf.ranges.aws_range import AWSRange
from src.app.core.cdktf.ranges.base_range import AbstractBaseRange
from src.app.enums.regions import OpenLabsRegion
from src.app.schemas.range_schemas import BlueprintRangeSchema
from src.app.schemas.secret_schema import SecretSchema
from tests.unit.core.cdktf.config import one_all_blueprint

pytestmark = pytest.mark.unit


# NOTE:
# This file is for testing base_range.py and the AbstractBaseRange class. Because
# the class is abstract we can't instantiate it and test it directly, so the AWSRange
# class is used instead as a stand in.


@pytest.fixture(scope="function")
def aws_range(
    range_factory: Callable[
        [type[AbstractBaseRange], BlueprintRangeSchema, OpenLabsRegion],
        AbstractBaseRange,
    ],
) -> AWSRange:
    """Synthesize AWS stack with one_all_blueprint."""
    # Call the factory with the desired stack, stack name, and region.
    range_instance = range_factory(
        AWSRange, one_all_blueprint, OpenLabsRegion.US_EAST_1
    )

    if not isinstance(range_instance, AWSRange):
        msg = f"Expected AWSRange, but got {type(range_instance)}"
        raise TypeError(msg)

    return range_instance


@pytest.fixture(scope="function")
def mock_deploy_success(aws_range: AWSRange, monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch over all functions in the .deploy() function so that it returns as if successful."""
    monkeypatch.setattr(aws_range, "is_synthesized", lambda: True)

    mock_init = AsyncMock(return_value=True)
    monkeypatch.setattr(aws_range, "_init", mock_init)

    mock_run_command = AsyncMock(return_value=("Mock stdout", "Mock stderr", 0))
    monkeypatch.setattr(aws_range, "_async_run_command", mock_run_command)

    # Mock checking statefile
    mock_aio_os_path_exists = AsyncMock(return_value=True)
    monkeypatch.setattr(aio_os_mock_target.path, "exists", mock_aio_os_path_exists)

    # Create a mock file object that has an async read() method
    mock_file_read = AsyncMock(return_value="""{"content": "State file contents."}""")

    mock_file_obj = MagicMock()
    mock_file_obj.__aenter__ = AsyncMock(return_value=mock_file_obj)
    mock_file_obj.__aexit__ = AsyncMock(return_value=None)
    mock_file_obj.read = mock_file_read
    monkeypatch.setattr(
        aiofiles_mock_target, "open", MagicMock(return_value=mock_file_obj)
    )

    mock_parse_output = AsyncMock(return_value="Fake range!")
    monkeypatch.setattr(aws_range, "_parse_terraform_outputs", mock_parse_output)

    # Patch synth cleanup
    mock_cleanup = AsyncMock(return_value=True)
    monkeypatch.setattr(aws_range, "cleanup_synth", mock_cleanup)


@pytest.fixture(scope="function")
def mock_destroy_success(aws_range: AWSRange, monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch over all functions in .destroy() function so that it returns as if successful."""
    # Ensure the range is deployed and synthesized
    monkeypatch.setattr(aws_range, "is_deployed", lambda: True)
    monkeypatch.setattr(aws_range, "is_synthesized", lambda: True)

    # Simulate successful creation of the state file
    mock_create_state_file = AsyncMock(return_value=True)
    monkeypatch.setattr(aws_range, "create_state_file", mock_create_state_file)

    # Mock checking statefile
    mock_aio_os_path_exists = AsyncMock(return_value=True)
    monkeypatch.setattr(aio_os_mock_target.path, "exists", mock_aio_os_path_exists)

    mock_init = AsyncMock(return_value=True)
    monkeypatch.setattr(aws_range, "_init", mock_init)

    mock_run_command = AsyncMock(return_value=("Mock stdout", "Mock stderr", 0))
    monkeypatch.setattr(aws_range, "_async_run_command", mock_run_command)

    # Patch synth cleanup
    mock_cleanup = AsyncMock(return_value=True)
    monkeypatch.setattr(aws_range, "cleanup_synth", mock_cleanup)


@pytest.fixture(scope="function")
def mock_async_run_command_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch over all functions in ._async_run_command() function so that it returns successfully."""
    # Mock checking synth dir
    mock_aio_os_path_exists = AsyncMock(return_value=True)
    monkeypatch.setattr(aio_os_mock_target.path, "exists", mock_aio_os_path_exists)

    # Patch subprocess execution
    mock_process = AsyncMock(spec=asyncio.subprocess.Process)
    mock_process.communicate.return_value = (b"Mock stdout", b"Mock stderr")
    mock_process.returncode = 0

    mock_subprocess_exec = AsyncMock(spec=asyncio, return_value=mock_process)
    monkeypatch.setattr(asyncio, "create_subprocess_exec", mock_subprocess_exec)


@pytest.fixture(scope="function")
def mock_init_success(aws_range: AWSRange, monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch over all functions in ._init() function so that it returns successfully."""
    mock_run_command = AsyncMock(return_value=("Mock stdout", "Mock stderr", 0))
    monkeypatch.setattr(aws_range, "_async_run_command", mock_run_command)


async def test_base_range_synthesize_exception(
    aws_range: AWSRange, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that aws range synthesize() returns False on exception."""

    def fake_get_provider_stack_class() -> None:
        msg = "Forced exception in get_provider_stack_class"
        raise Exception(msg)

    # Patch get_provider_stack_class with the fake function.
    monkeypatch.setattr(
        aws_range, "get_provider_stack_class", fake_get_provider_stack_class
    )

    # Calling synthesize() should now catch the exception and return False.
    result = await aws_range.synthesize()
    assert result is False


def test_base_range_not_synthesized_state_on_init(aws_range: AWSRange) -> None:
    """Test that aws range objects sythesized state variable is false on init."""
    assert not aws_range.is_synthesized()


async def test_base_range_sythesized_state_after_synth(aws_range: AWSRange) -> None:
    """Test that aws range objects synthesized state variable is truth after synth() call."""
    assert await aws_range.synthesize()
    assert aws_range.is_synthesized()


async def test_base_range_no_destroy_not_synthesized(aws_range: AWSRange) -> None:
    """Test that aws range.destroy() returns false when range object not synthesized yet."""
    assert not await aws_range.destroy()


async def test_base_range_no_deploy_not_synthesized(aws_range: AWSRange) -> None:
    """Test that the aws range.deploy() returns false when range object not synthesized yet."""
    assert not await aws_range.deploy()


def test_base_range_not_deployed_state_when_no_state_file_init(
    aws_range: AWSRange,
) -> None:
    """Test that the aws range is_deployed state variable is false when no state_file is passed in on init."""
    assert not aws_range.is_deployed()


def test_base_range_init_with_state_file() -> None:
    """Test that is_deployed() returns True when we initialize with a state_file."""
    test_state_file = {"test": "Test content"}

    aws_range = AWSRange(
        name="test-range",
        range_obj=one_all_blueprint,
        region=OpenLabsRegion.US_EAST_1,
        description="Test description.",
        secrets=SecretSchema(),
        state_file=test_state_file,
    )

    assert aws_range.is_deployed()


def test_base_range_get_state_file_none_when_no_state_file_init(
    aws_range: AWSRange,
) -> None:
    """Test that the base range get_state_file() returns None when no state_file is passed in on init."""
    assert aws_range.get_state_file() is None


def test_base_range_get_state_file_with_content(aws_range: AWSRange) -> None:
    """Test that aws range get_state_file() returns the state_file variable content."""
    test_state_file = {"test": "Test content"}
    aws_range.state_file = test_state_file
    assert aws_range.get_state_file() == test_state_file


def test_base_range_get_state_file_path(aws_range: AWSRange) -> None:
    """Test that the aws range get_state_file_path() returns the correct path."""
    correct_path = (
        aws_range.get_synth_dir() / f"terraform.{aws_range.stack_name}.tfstate"
    )
    assert aws_range.get_state_file_path() == correct_path


async def test_base_range_create_state_file_no_content(aws_range: AWSRange) -> None:
    """Test that the aws range create_state_file() returns false when no state_file content available."""
    assert not await aws_range.create_state_file()


async def test_base_range_create_state_file(aws_range: AWSRange) -> None:
    """Test that the aws range create_state_file() creates a correct state file."""
    test_state_file = {"test": "Test content"}
    aws_range.state_file = test_state_file

    assert await aws_range.synthesize()
    assert await aws_range.create_state_file()

    # Test correct content
    state_file_content = ""
    with open(aws_range.get_state_file_path(), mode="r") as file:
        state_file_content = file.read()

    assert state_file_content, "State file is empty when it should have content!"

    loaded_state_file_content = json.loads(state_file_content)
    assert loaded_state_file_content == test_state_file


async def test_base_range_cleanup_synth(aws_range: AWSRange) -> None:
    """Test that aws range cleanup_synth() works after synthesis."""
    assert await aws_range.synthesize(), "Failed to synthesize AWS range object!"
    assert await aws_range.cleanup_synth()


async def test_base_range_cleanup_synth_exception(
    aws_range: AWSRange, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that aws range cleanup_synth() returns False on exception."""

    # Define a fake rmtree function that always raises an exception.
    def fake_rmtree(path: str, ignore_errors: bool = False) -> None:
        msg = "Forced exception for testing"
        raise OSError(msg)

    # Override shutil.rmtree with our fake function.
    monkeypatch.setattr(shutil, "rmtree", fake_rmtree)

    # Call the cleanup_synth method; it should catch the exception and return False.
    result = await aws_range.cleanup_synth()
    assert result is False


async def test_base_range_deploy_success(
    aws_range: AWSRange, mock_deploy_success: None
) -> None:
    """Test that .deploy() returns a truthy value when it succeeds."""
    assert await aws_range.deploy()  # None means deploy failed


async def test_base_range_deploy_init_error(
    aws_range: AWSRange,
    mock_deploy_success: None,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that deploy() returns a falsy value and doesn't auto clean up.

    No auto clean up because we never reached terraform apply so no resources were
    created.
    """
    mock_run_command = AsyncMock(return_value=False)
    monkeypatch.setattr(aws_range, "_init", mock_run_command)

    # Patch over auto destroy logic
    mock_destroy = AsyncMock(return_value=True)
    monkeypatch.setattr(aws_range, "destroy", mock_destroy)

    # Patch synth cleanup
    mock_cleanup = AsyncMock(return_value=True)
    monkeypatch.setattr(aws_range, "cleanup_synth", mock_cleanup)

    # Validate called
    assert not await aws_range.deploy()  # None means deploy failed
    mock_destroy.assert_not_awaited()  # Validate we did NOT auto destroy
    mock_cleanup.assert_awaited_once()  # Validate we clean up synth files

    # Check that we properly logger.exception() errors
    except_log_keywords = "init failed"
    assert any(
        record.levelno == logging.ERROR
        and record.exc_info is not None
        and except_log_keywords in record.message.lower()
        for record in caplog.records
    )


async def test_base_range_deploy_exception(
    aws_range: AWSRange,
    mock_deploy_success: None,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that deploy() returns a falsy value and auto cleans up after running terraform apply.

    This is when we get a generic error during the deploy sequence.

    """
    mock_run_command = AsyncMock(side_effect=Exception("Mock runtime error!"))
    monkeypatch.setattr(aws_range, "_async_run_command", mock_run_command)

    # Patch over auto destroy logic
    mock_destroy = AsyncMock(return_value=True)
    monkeypatch.setattr(aws_range, "destroy", mock_destroy)

    # Patch synth cleanup
    mock_cleanup = AsyncMock(return_value=True)
    monkeypatch.setattr(aws_range, "cleanup_synth", mock_cleanup)

    # Validate called
    assert not await aws_range.deploy()  # None means deploy failed
    mock_destroy.assert_awaited_once()  # Validate we auto destroy
    mock_cleanup.assert_awaited_once()  # Validate we clean up synth files

    # Check that we properly logger.exception() errors
    except_log_keywords = "error during deployment"
    assert any(
        record.levelno == logging.ERROR
        and record.exc_info is not None
        and except_log_keywords in record.message.lower()
        for record in caplog.records
    )


async def test_base_range_deploy_subprocess_error(
    aws_range: AWSRange,
    mock_deploy_success: None,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that deploy() returns a falsy value and auto cleans up if terraform apply fails."""
    mock_run_command = AsyncMock(return_value=("Mock stdout", "Mock stderr", 1))
    monkeypatch.setattr(aws_range, "_async_run_command", mock_run_command)

    # Patch over auto destroy logic
    mock_destroy = AsyncMock(return_value=True)
    monkeypatch.setattr(aws_range, "destroy", mock_destroy)

    # Patch synth cleanup
    mock_cleanup = AsyncMock(return_value=True)
    monkeypatch.setattr(aws_range, "cleanup_synth", mock_cleanup)

    # Validate called
    assert not await aws_range.deploy()  # None means deploy failed
    mock_destroy.assert_awaited_once()  # Validate we auto destroy
    mock_cleanup.assert_awaited_once()  # Validate we clean up synth files

    # Check that we properly logger.exception() errors
    except_log_keywords = "apply failed"
    assert any(
        record.levelno == logging.ERROR
        and record.exc_info is not None
        and except_log_keywords in record.message.lower()
        for record in caplog.records
    )


async def test_base_range_deploy_no_state_file(
    aws_range: AWSRange,
    mock_deploy_success: None,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that deploy() returns falsy value when no state file is found after deploying the range."""
    # Mock reading statefile
    mock_aio_os_path_exists = AsyncMock(return_value=False)
    monkeypatch.setattr(aio_os_mock_target.path, "exists", mock_aio_os_path_exists)

    assert not await aws_range.deploy()  # None means deploy failed

    # Check that we properly logger.exception() errors
    except_log_keywords = "state file"
    assert any(
        record.levelno == logging.ERROR
        and record.exc_info is not None
        and except_log_keywords in record.message.lower()
        for record in caplog.records
    )


async def test_base_range_deploy_no_parsed_output(
    aws_range: AWSRange,
    mock_deploy_success: None,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that we get a falsy value when we can't parse the output of the terraform apply."""
    # Patch parsing
    mock_parse_output = AsyncMock(return_value=None)
    monkeypatch.setattr(aws_range, "_parse_terraform_outputs", mock_parse_output)

    # Patch over auto destroy logic
    mock_destroy = AsyncMock(return_value=True)
    monkeypatch.setattr(aws_range, "destroy", mock_destroy)

    # Patch synth cleanup
    mock_cleanup = AsyncMock(return_value=True)
    monkeypatch.setattr(aws_range, "cleanup_synth", mock_cleanup)

    # Validate
    assert not await aws_range.deploy()
    mock_destroy.assert_awaited_once()  # Verify that we auto destroy
    mock_cleanup.assert_awaited_once()  # and cleanup

    # Check that we properly logger.exception() exceptions
    except_log_keywords = "parse terraform outputs"
    assert any(
        record.levelno == logging.ERROR
        and record.exc_info is not None
        and except_log_keywords in record.message.lower()
        for record in caplog.records
    )


async def test_base_range_destroy_success(
    aws_range: AWSRange,
    mock_destroy_success: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that destroy() returns True when it succeeds."""
    assert await aws_range.destroy() is True


async def test_base_range_destroy_create_state_file_failure_fallback(
    aws_range: AWSRange, mock_destroy_success: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that destroy() fallback to using an existing state file when it can't create one itself.

    This would simulate calling .destroy() for auto cleaning up a failed .deploy() where
    the range object raised an exception before saving the state file while deploying.

    """
    # Simulate failed creation of the state file
    mock_create_state_file = AsyncMock(return_value=False)
    monkeypatch.setattr(aws_range, "create_state_file", mock_create_state_file)

    assert await aws_range.destroy() is True


async def test_base_range_destroy_no_state_file_failure(
    aws_range: AWSRange, mock_destroy_success: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that destroy() fails when we can't create or find a state file to use when destroying."""
    # Simulate failure creation of the state file
    mock_create_state_file = AsyncMock(return_value=False)
    monkeypatch.setattr(aws_range, "create_state_file", mock_create_state_file)

    # Mock no existing state file
    mock_aio_os_path_exists = AsyncMock(return_value=False)
    monkeypatch.setattr(aio_os_mock_target.path, "exists", mock_aio_os_path_exists)

    assert await aws_range.destroy() is False


async def test_base_range_destroy_not_synthesized(
    aws_range: AWSRange, mock_destroy_success: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that destroy() returns False when it's not synthesized."""
    monkeypatch.setattr(aws_range, "is_synthesized", lambda: False)

    assert await aws_range.destroy() is False


async def test_base_range_destroy_not_deployed(
    aws_range: AWSRange, mock_destroy_success: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that destroy() returns False when it's not deployed."""
    monkeypatch.setattr(aws_range, "is_deployed", lambda: False)

    assert await aws_range.destroy() is False


async def test_base_range_destroy_init_error(
    aws_range: AWSRange,
    mock_destroy_success: None,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that destroy() returns a falsy value and doesn't auto clean up."""
    mock_run_command = AsyncMock(return_value=False)
    monkeypatch.setattr(aws_range, "_init", mock_run_command)

    # Patch synth cleanup
    mock_cleanup = AsyncMock(return_value=True)
    monkeypatch.setattr(aws_range, "cleanup_synth", mock_cleanup)

    # Validate called
    assert not await aws_range.destroy()  # None means deploy failed
    mock_cleanup.assert_awaited_once()  # Validate we clean up synth files

    # Check that we properly logger.exception() errors
    except_log_keywords = "init failed"
    assert any(
        record.levelno == logging.ERROR
        and record.exc_info is not None
        and except_log_keywords in record.message.lower()
        for record in caplog.records
    )


async def test_base_range_destroy_subprocess_error(
    aws_range: AWSRange,
    mock_destroy_success: None,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that destroy() returns false when terraform destroy fails."""
    mock_run_command = AsyncMock(return_value=("Mock stdout", "Mock stderr", 1))
    monkeypatch.setattr(aws_range, "_async_run_command", mock_run_command)

    # Patch synth cleanup
    mock_cleanup = AsyncMock(return_value=True)
    monkeypatch.setattr(aws_range, "cleanup_synth", mock_cleanup)

    # Validate called
    assert not await aws_range.destroy()  # None means deploy failed
    mock_cleanup.assert_awaited_once()  # Validate we clean up synth files

    # Check that we properly logger.exception() errors
    except_log_keywords = "destroy failed"
    assert any(
        record.levelno == logging.ERROR
        and record.exc_info is not None
        and except_log_keywords in record.message.lower()
        for record in caplog.records
    )


async def test_base_range_parse_terraform_outputs(
    aws_range: AWSRange, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test parse_terraform_output() returns None when the state file doesn't exist."""
    monkeypatch.setattr(
        aws_range, "get_state_file_path", lambda: Path("/does/not/exist")
    )

    assert await aws_range._parse_terraform_outputs() is None


async def test_base_range_parse_terraform_outputs_subprocess_error(
    aws_range: AWSRange,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    tmp_path: Path,
) -> None:
    """Test that parse_terraform_output() returns None when subprocess.run raises CalledProcessError."""
    # Mock checking statefile
    mock_aio_os_path_exists = AsyncMock(return_value=True)
    monkeypatch.setattr(aio_os_mock_target.path, "exists", mock_aio_os_path_exists)

    # Mock failed command execution
    mock_run_command = AsyncMock(return_value=("Mock stdout", "Mock stderr", 1))
    monkeypatch.setattr(aws_range, "_async_run_command", mock_run_command)

    assert not await aws_range._parse_terraform_outputs()

    # Check that we properly logger.exception() errors
    except_log_keywords = "terraform output"
    assert any(
        record.levelno == logging.ERROR
        and record.exc_info is not None
        and except_log_keywords in record.message.lower()
        for record in caplog.records
    )


async def test_base_range_parse_terraform_outputs_no_output(
    aws_range: AWSRange,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    tmp_path: Path,
) -> None:
    """Test that parse_terraform_output() returns None when there is no valid terraform output."""
    # Mock checking statefile
    mock_aio_os_path_exists = AsyncMock(return_value=True)
    monkeypatch.setattr(aio_os_mock_target.path, "exists", mock_aio_os_path_exists)

    # Mock failed command execution
    mock_run_command = AsyncMock(return_value=("", "Mock stderr", 0))
    monkeypatch.setattr(aws_range, "_async_run_command", mock_run_command)

    assert not await aws_range._parse_terraform_outputs()

    # Check that we properly logger.exception() errors
    except_log_keywords = "terraform output"
    assert any(
        record.levelno == logging.ERROR
        and except_log_keywords in record.message.lower()
        for record in caplog.records
    )


async def test_base_range_parse_terraform_outputs_keyerror(
    aws_range: AWSRange,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    tmp_path: Path,
) -> None:
    """Test that parse_terraform_output() returns None it recieves a KeyError when parsing the state file."""
    # Mock checking statefile
    mock_aio_os_path_exists = AsyncMock(return_value=True)
    monkeypatch.setattr(aio_os_mock_target.path, "exists", mock_aio_os_path_exists)

    # Mock failed command execution
    bad_stdout = """{"fake-JumpboxInstanceId": {"nothing": "to see here"}, "fake-JumpboxPublicIp": "hi", "fake-private-key": "not so private :)"}"""
    mock_run_command = AsyncMock(return_value=(bad_stdout, "Mock stderr", 0))
    monkeypatch.setattr(aws_range, "_async_run_command", mock_run_command)

    assert not await aws_range._parse_terraform_outputs()

    # Check that we properly logger.exception() errors
    except_log_keywords = "missing key"
    assert any(
        record.levelno == logging.ERROR
        and record.exc_info is not None
        and except_log_keywords in record.message.lower()
        for record in caplog.records
    )


async def test_base_range_parse_terraform_outputs_generic_exception(
    aws_range: AWSRange,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    tmp_path: Path,
) -> None:
    """Test that parse_terraform_output() returns None it recieves a generic exception when parsing the state file."""
    # Arrange: Mock dependencies to force an IndexError during parsing
    state_file = tmp_path / "terraform.tfstate"
    state_file.touch()
    monkeypatch.setattr(aws_range, "get_state_file_path", lambda: state_file)
    monkeypatch.setattr(os, "chdir", lambda path: None)

    stdout = """{"a-JumpboxInstanceId":{"value":"id"},"b-JumpboxPublicIp":{"value":"ip"},"c-private-key":{"value":"pk"}}"""
    mock_run_command = AsyncMock(return_value=(stdout, "Mock stderr", 0))
    monkeypatch.setattr(aws_range, "_async_run_command", mock_run_command)

    # Force an IndexError by creating a mismatch in VPC counts
    malformed_dump = aws_range.range_obj.model_dump()
    malformed_dump["vpcs"] = []
    monkeypatch.setattr(
        BlueprintRangeSchema, "model_dump", lambda *args, **kwargs: malformed_dump
    )

    assert not await aws_range._parse_terraform_outputs()

    # Assert that the correct exception was logged
    assert any(
        "unknown error parsing terraform outputs" in record.message.lower()
        and record.levelno == logging.ERROR
        and record.exc_info is not None
        for record in caplog.records
    )


async def test_base_range_async_run_command_no_synth_dir(
    aws_range: AWSRange,
    monkeypatch: pytest.MonkeyPatch,
    mock_async_run_command_success: None,
) -> None:
    """Test that the async run command helper raises a FileNotFound exception when synth dir doesn't exist."""
    # Mock checking synth dir
    mock_aio_os_path_exists = AsyncMock(return_value=False)
    monkeypatch.setattr(aio_os_mock_target.path, "exists", mock_aio_os_path_exists)

    with pytest.raises(FileNotFoundError):
        await aws_range._async_run_command(["ls"])


async def test_base_range_async_run_command_no_credentials(
    aws_range: AWSRange,
    monkeypatch: pytest.MonkeyPatch,
    mock_async_run_command_success: None,
) -> None:
    """Test that we do not add range/cloud credentials to the environment variables when with_creds=False."""
    mock_cred_vars = MagicMock()
    monkeypatch.setattr(aws_range, "get_cred_env_vars", mock_cred_vars)

    assert await aws_range._async_run_command(["ls"], with_creds=False)
    mock_cred_vars.assert_not_called()

    # Ensure that no creds are passed by default
    assert await aws_range._async_run_command(["ls"])
    mock_cred_vars.assert_not_called()


async def test_base_range_async_run_command_with_credentials(
    aws_range: AWSRange,
    monkeypatch: pytest.MonkeyPatch,
    mock_async_run_command_success: None,
) -> None:
    """Test that we do add range/cloud credentials to the environment variables when with_creds=True."""
    mock_cred_vars = MagicMock()
    monkeypatch.setattr(aws_range, "get_cred_env_vars", mock_cred_vars)

    assert await aws_range._async_run_command(["ls"], with_creds=True)
    mock_cred_vars.assert_called_once()


async def test_base_range_async_run_command_output_logging(
    aws_range: AWSRange,
    mock_async_run_command_success: None,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that we log output as INFO logs and errors as WARNING logs."""
    # Tack on a uuid to ensure the return values
    # are acutally being logged properly
    unique_uuid = uuid.uuid4()
    test_stdout = f"Mock stdout {unique_uuid}"
    test_stderr = f"Mock stderr {unique_uuid}"

    # Patch subprocess execution
    mock_process = AsyncMock(spec=asyncio.subprocess.Process)
    mock_process.communicate.return_value = (test_stdout.encode(), test_stderr.encode())
    mock_process.returncode = 0

    mock_subprocess_exec = AsyncMock(spec=asyncio, return_value=mock_process)
    monkeypatch.setattr(asyncio, "create_subprocess_exec", mock_subprocess_exec)

    assert await aws_range._async_run_command(["ls"])

    # INFO for stdout
    assert any(
        test_stdout.lower() in record.message.lower()
        for record in caplog.records
        if record.levelno == logging.INFO
    )

    # WARNING for stderr
    assert any(
        test_stderr.lower() in record.message.lower()
        for record in caplog.records
        if record.levelno == logging.WARNING
    )


async def test_base_range_init_success(
    aws_range: AWSRange, mock_init_success: None
) -> None:
    """Test _init() returns true when the terraform init command completes successfully."""
    assert await aws_range._init()


async def test_base_range_init_failed(
    aws_range: AWSRange, mock_init_success: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that _init() returns false when the terraform init command fails."""
    # Return not 0
    mock_run_command = AsyncMock(return_value=("Mock stdout", "Mock stderr", 1))
    monkeypatch.setattr(aws_range, "_async_run_command", mock_run_command)

    assert not await aws_range._init()
