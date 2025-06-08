import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Callable
from unittest.mock import Mock

import pytest

from src.app.core.cdktf.ranges.aws_range import AWSRange
from src.app.core.cdktf.ranges.base_range import AbstractBaseRange
from src.app.enums.regions import OpenLabsRegion
from src.app.schemas.range_schemas import BlueprintRangeSchema
from src.app.schemas.secret_schema import SecretSchema
from tests.unit.core.cdktf.cdktf_mocks import (
    DummyPath,
    fake_open,
    fake_run_exception,
    fake_subprocess_run_cpe,
)
from tests.unit.core.cdktf.config import one_all_blueprint

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
) -> AbstractBaseRange:
    """Synthesize AWS stack with one_all_blueprint."""
    # Call the factory with the desired stack, stack name, and region.
    return range_factory(AWSRange, one_all_blueprint, OpenLabsRegion.US_EAST_1)


def test_base_range_synthesize_exception(
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
    result = aws_range.synthesize()
    assert result is False


def test_base_range_not_synthesized_state_on_init(aws_range: AWSRange) -> None:
    """Test that aws range objects sythesized state variable is false on init."""
    assert not aws_range.is_synthesized()


def test_base_range_sythesized_state_after_synth(aws_range: AWSRange) -> None:
    """Test that aws range objects synthesized state variable is truth after synth() call."""
    assert aws_range.synthesize()
    assert aws_range.is_synthesized()


def test_base_range_no_destroy_not_synthesized(aws_range: AWSRange) -> None:
    """Test that aws range.destroy() returns false when range object not synthesized yet."""
    assert not aws_range.destroy()


def test_base_range_no_deploy_not_synthesized(aws_range: AWSRange) -> None:
    """Test that the aws range.deploy() returns false when range object not synthesized yet."""
    assert not aws_range.deploy()


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
    """Test that the aws range get_state_file() returns None when no state_file is passed in on init."""
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


def test_base_range_create_state_file_no_content(aws_range: AWSRange) -> None:
    """Test that the aws range create_state_file() returns false when no state_file content available."""
    assert not aws_range.create_state_file()


def test_base_range_create_state_file(aws_range: AWSRange) -> None:
    """Test that the aws range create_state_file() creates a correct state file."""
    test_state_file = {"test": "Test content"}
    aws_range.state_file = test_state_file

    assert aws_range.synthesize()
    assert aws_range.create_state_file()

    # Test correct content
    state_file_content = ""
    with open(aws_range.get_state_file_path(), mode="r") as file:
        state_file_content = file.read()

    assert state_file_content, "State file is empty when it should have content!"

    loaded_state_file_content = json.loads(state_file_content)
    assert loaded_state_file_content == test_state_file


def test_base_range_cleanup_synth(aws_range: AWSRange) -> None:
    """Test that aws range cleanup_synth() works after synthesis."""
    assert aws_range.synthesize(), "Failed to synthesize AWS range object!"
    assert aws_range.cleanup_synth()


def test_base_range_cleanup_synth_exception(
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
    result = aws_range.cleanup_synth()
    assert result is False


def test_base_range_deploy_success(
    aws_range: AWSRange, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that deploy() returns True when subprocess commands succeed."""
    # Ensure the range is synthesized
    monkeypatch.setattr(aws_range, "is_synthesized", lambda: True)

    # Patch subprocess.run to simulate successful execution (no exceptions raised)
    monkeypatch.setattr(subprocess, "run", lambda cmd, check, **kwargs: None)

    # Patch os.chdir to prevent actual directory changes
    monkeypatch.setattr(os, "chdir", lambda x: None)

    # Create a dummy Path-like object for get_state_file_path and get_synth_dir
    dummy_path = DummyPath()
    dummy_path.exists.return_value = True

    monkeypatch.setattr(aws_range, "get_state_file_path", lambda: DummyPath())
    monkeypatch.setattr(aws_range, "get_synth_dir", lambda: DummyPath())
    monkeypatch.setattr(
        aws_range, "_parse_terraform_outputs", lambda: {"fake": "output range"}
    )

    # Patch cleanup_synth to simulate successful cleanup
    monkeypatch.setattr(aws_range, "cleanup_synth", lambda: True)

    # Patch open to simulate reading a valid JSON state file
    monkeypatch.setattr(
        "builtins.open",
        fake_open,
    )

    assert aws_range.deploy()  # None means deploy failed


def test_base_range_deploy_calledprocesserror(
    aws_range: AWSRange,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that deploy() returns False when subprocess.run raises CalledProcessError."""
    monkeypatch.setattr(aws_range, "is_synthesized", lambda: True)
    monkeypatch.setattr(subprocess, "run", fake_subprocess_run_cpe)
    monkeypatch.setattr(os, "chdir", lambda x: None)

    # Create a dummy Path-like object for get_state_file_path and get_synth_dir
    dummy_path = DummyPath()
    dummy_path.exists.return_value = True

    monkeypatch.setattr(aws_range, "get_state_file_path", lambda: DummyPath())
    monkeypatch.setattr(aws_range, "cleanup_synth", lambda: True)

    # Patch over auto destroy logic
    mock_destroy = Mock()
    mock_destroy.return_value = True
    monkeypatch.setattr(aws_range, "destroy", mock_destroy)

    assert not aws_range.deploy()  # None means deploy failed
    mock_destroy.assert_called_once()  # Validate we auto destroy

    # Check that we properly logger.exception() subprocess errors
    except_log_keywords = "terraform command"
    assert any(
        record.levelno == logging.ERROR
        and record.exc_info is not None
        and except_log_keywords in record.message.lower()
        for record in caplog.records
    )


def test_base_range_deploy_exception(
    aws_range: AWSRange,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that deploy() returns False when subprocess.run raises a general exception."""
    monkeypatch.setattr(aws_range, "is_synthesized", lambda: True)
    monkeypatch.setattr(subprocess, "run", fake_run_exception)
    monkeypatch.setattr(os, "chdir", lambda x: None)

    # Create a dummy Path-like object for get_state_file_path and get_synth_dir
    dummy_path = DummyPath()
    dummy_path.exists.return_value = True

    monkeypatch.setattr(aws_range, "get_state_file_path", lambda: DummyPath())
    monkeypatch.setattr(aws_range, "cleanup_synth", lambda: True)

    # Patch over auto destroy logic
    mock_destroy = Mock()
    mock_destroy.return_value = True
    monkeypatch.setattr(aws_range, "destroy", mock_destroy)

    assert not aws_range.deploy()  # None means deploy failed
    mock_destroy.assert_called_once()  # Validate we auto destroy

    # Check that we properly logger.exception() subprocess errors
    except_log_keywords = "error during deployment"
    assert any(
        record.levelno == logging.ERROR
        and record.exc_info is not None
        and except_log_keywords in record.message.lower()
        for record in caplog.records
    )


def test_base_range_deploy_no_state_file(
    aws_range: AWSRange, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that deploy() returns False when no state file is found after deploying the range."""
    # Ensure the range is synthesized
    monkeypatch.setattr(aws_range, "is_synthesized", lambda: True)

    # Patch subprocess.run to simulate successful execution (no exceptions raised)
    monkeypatch.setattr(subprocess, "run", lambda cmd, check, **kwargs: None)

    # Patch os.chdir to prevent actual directory changes
    monkeypatch.setattr(os, "chdir", lambda x: None)

    # Create a dummy Path-like object that returns False to simulate no state file
    dummy_path_no_exist = DummyPath()
    dummy_path_no_exist.exists.return_value = False

    monkeypatch.setattr(aws_range, "get_state_file_path", lambda: dummy_path_no_exist)
    monkeypatch.setattr(aws_range, "get_synth_dir", lambda: DummyPath())

    assert not aws_range.deploy()  # None means deploy failed


def test_base_range_deploy_no_parsed_output(
    aws_range: AWSRange,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    tmp_path: Path,
) -> None:
    """Test that deploy() returns True when subprocess commands succeed."""
    # Ensure the range is synthesized
    monkeypatch.setattr(aws_range, "is_synthesized", lambda: True)

    # Patch subprocess.run to simulate successful execution (no exceptions raised)
    monkeypatch.setattr(subprocess, "run", lambda cmd, check, **kwargs: None)

    # Patch os.chdir to prevent actual directory changes
    monkeypatch.setattr(os, "chdir", lambda x: None)

    # Create a dummy Path-like object for get_state_file_path and get_synth_dir
    dummy_path = DummyPath()
    dummy_path.exists.return_value = True

    monkeypatch.setattr(aws_range, "get_state_file_path", lambda: DummyPath())
    monkeypatch.setattr(aws_range, "get_synth_dir", lambda: DummyPath())

    # No paresed output
    monkeypatch.setattr(aws_range, "_parse_terraform_outputs", lambda: None)

    # Patch cleanup_synth to simulate successful cleanup
    monkeypatch.setattr(aws_range, "cleanup_synth", lambda: True)

    # Patch open to simulate reading a valid JSON state file
    monkeypatch.setattr(
        "builtins.open",
        fake_open,
    )
    # Patch over auto destroy logic
    mock_destroy = Mock()
    mock_destroy.return_value = True
    monkeypatch.setattr(aws_range, "destroy", mock_destroy)

    assert not aws_range.deploy()  # None means deploy failed
    mock_destroy.assert_called_once()  # Validate we auto destroy

    # Check that we properly logger.exception() exceptions
    except_log_keywords = "parse terraform outputs"
    assert any(
        record.levelno == logging.ERROR
        and record.exc_info is not None
        and except_log_keywords in record.message.lower()
        for record in caplog.records
    )


def test_base_range_destroy_success(
    aws_range: AWSRange,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Test that destroy() returns True when subprocess commands succeed."""
    # Ensure the range is deployed and synthesized
    monkeypatch.setattr(aws_range, "is_deployed", lambda: True)
    monkeypatch.setattr(aws_range, "is_synthesized", lambda: True)

    # Simulate successful creation of the state file
    monkeypatch.setattr(aws_range, "create_state_file", lambda: True)

    # Fake statefile
    fake_state_file_path = tmp_path / "terraform.tfstate"
    fake_state_file_path.touch()
    monkeypatch.setattr(aws_range, "get_state_file_path", lambda: fake_state_file_path)

    # Return empty credential environment variables
    monkeypatch.setattr(aws_range, "get_cred_env_vars", lambda: {})

    # Patch subprocess.run to simulate successful execution (no exceptions)
    monkeypatch.setattr(subprocess, "run", lambda cmd, check, **kwargs: None)

    # Prevent actual directory changes
    monkeypatch.setattr(os, "chdir", lambda x: None)

    # Patch get_synth_dir to return a DummyPath instance
    monkeypatch.setattr(aws_range, "get_synth_dir", lambda: DummyPath())

    # Simulate successful cleanup of synthesis files
    monkeypatch.setattr(aws_range, "cleanup_synth", lambda: True)

    result = aws_range.destroy()
    assert result is True


def test_base_range_destroy_calledprocesserror(
    aws_range: AWSRange,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    tmp_path: Path,
) -> None:
    """Test that destroy() returns False when subprocess.run raises CalledProcessError."""
    monkeypatch.setattr(aws_range, "is_deployed", lambda: True)
    monkeypatch.setattr(aws_range, "is_synthesized", lambda: True)
    monkeypatch.setattr(aws_range, "create_state_file", lambda: True)
    monkeypatch.setattr(aws_range, "get_cred_env_vars", lambda: {})

    # Patch subprocess.run to raise a CalledProcessError
    monkeypatch.setattr(subprocess, "run", fake_subprocess_run_cpe)
    monkeypatch.setattr(os, "chdir", lambda x: None)
    monkeypatch.setattr(aws_range, "get_synth_dir", lambda: DummyPath())
    monkeypatch.setattr(aws_range, "cleanup_synth", lambda: True)

    # Patch state file operations
    fake_state_file = tmp_path / "terraform.tfstate"
    fake_state_file.touch()

    # Patch state file functions
    monkeypatch.setattr(aws_range, "get_state_file_path", lambda: fake_state_file)
    monkeypatch.setattr(os, "chdir", lambda path: None)

    result = aws_range.destroy()
    assert result is False

    # Check that we properly logger.exception() subprocess errors
    except_log_keywords = "terraform command failed"
    assert any(
        record.levelno == logging.ERROR
        and record.exc_info is not None
        and except_log_keywords in record.message.lower()
        for record in caplog.records
    )


def test_base_range_destroy_create_state_file_failure(
    aws_range: AWSRange, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that destroy() returns False when create_state_file() fails."""
    monkeypatch.setattr(aws_range, "is_deployed", lambda: True)
    monkeypatch.setattr(aws_range, "is_synthesized", lambda: True)
    monkeypatch.setattr(aws_range, "get_synth_dir", lambda: DummyPath())

    # Prevent actual directory changes
    monkeypatch.setattr(os, "chdir", lambda x: None)

    # Simulate failure in state file creation
    monkeypatch.setattr(aws_range, "create_state_file", lambda: False)

    result = aws_range.destroy()
    assert result is False


def test_base_range_destroy_not_synthesized(
    aws_range: AWSRange, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that destroy() returns False when it's not synthesized."""
    monkeypatch.setattr(aws_range, "is_deployed", lambda: True)
    monkeypatch.setattr(aws_range, "is_synthesized", lambda: False)

    result = aws_range.destroy()
    assert result is False


def test_base_range_parse_terraform_outputs(
    aws_range: AWSRange, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test parse_terraform_output() returns nothing when the state file doesn't exist."""
    monkeypatch.setattr(
        aws_range, "get_state_file_path", lambda: Path("/does/not/exist")
    )

    assert not aws_range._parse_terraform_outputs()


def test_base_range_parse_terraform_outputs_calledprocesserror(
    aws_range: AWSRange,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    tmp_path: Path,
) -> None:
    """Test that parse_terraform_output() returns None when subprocess.run raises CalledProcessError."""
    fake_state_file = tmp_path / "terraform.tfstate"
    fake_state_file.touch()

    # Patch state file functions
    monkeypatch.setattr(aws_range, "get_state_file_path", lambda: fake_state_file)
    monkeypatch.setattr(os, "chdir", lambda path: None)

    # Patch subprocess.run to raise a CalledProcessError
    monkeypatch.setattr(subprocess, "run", fake_subprocess_run_cpe)

    assert not aws_range._parse_terraform_outputs()

    # Check that we properly logger.exception() subprocess errors
    except_log_keywords = "terraform outputs"
    assert any(
        record.levelno == logging.ERROR
        and record.exc_info is not None
        and except_log_keywords in record.message.lower()
        for record in caplog.records
    )


def test_base_range_parse_terraform_outputs_no_output(
    aws_range: AWSRange,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    tmp_path: Path,
) -> None:
    """Test that parse_terraform_output() returns None when there is no valid terraform output."""
    fake_state_file = tmp_path / "terraform.tfstate"
    fake_state_file.touch()

    # Patch state file functions
    monkeypatch.setattr(aws_range, "get_state_file_path", lambda: fake_state_file)
    monkeypatch.setattr(os, "chdir", lambda path: None)

    # Patch subprocess.run to raise a CalledProcessError
    mock_result = Mock()
    mock_result.stdout = "{}"
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: mock_result)

    assert not aws_range._parse_terraform_outputs()

    # Check that we properly logger.exception() subprocess errors
    except_log_keywords = "terraform output"
    assert any(
        record.levelno == logging.ERROR
        and except_log_keywords in record.message.lower()
        for record in caplog.records
    )


def test_base_range_parse_terraform_outputs_keyerror(
    aws_range: AWSRange,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    tmp_path: Path,
) -> None:
    """Test that parse_terraform_output() returns None it recieves a KeyError when parsing the state file."""
    fake_state_file = tmp_path / "terraform.tfstate"
    fake_state_file.touch()

    # Patch state file functions
    monkeypatch.setattr(aws_range, "get_state_file_path", lambda: fake_state_file)
    monkeypatch.setattr(os, "chdir", lambda path: None)

    # Patch subprocess.run to raise a CalledProcessError
    mock_result = Mock()
    mock_result.stdout = """{"fake-JumpboxInstanceId": {"nothing": "to see here"}, "fake-JumpboxPublicIp": "hi", "fake-private-key": "not so private :)"}"""
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: mock_result)

    assert not aws_range._parse_terraform_outputs()

    # Check that we properly logger.exception() subprocess errors
    except_log_keywords = "missing key"
    assert any(
        record.levelno == logging.ERROR
        and record.exc_info is not None
        and except_log_keywords in record.message.lower()
        for record in caplog.records
    )


def test_parse_terraform_outputs_generic_exception(
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

    mock_run_result = Mock(
        stdout='{"a-JumpboxInstanceId":{"value":"id"},"b-JumpboxPublicIp":{"value":"ip"},"c-private-key":{"value":"pk"}}'
    )
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: mock_run_result)

    # Force an IndexError by creating a mismatch in VPC counts
    malformed_dump = aws_range.range_obj.model_dump()
    malformed_dump["vpcs"] = []
    monkeypatch.setattr(
        BlueprintRangeSchema, "model_dump", lambda *args, **kwargs: malformed_dump
    )

    assert not aws_range._parse_terraform_outputs()

    # Assert that the correct exception was logged
    assert any(
        "unknown error parsing terraform outputs" in record.message.lower()
        and record.levelno == logging.ERROR
        and record.exc_info is not None
        for record in caplog.records
    )
