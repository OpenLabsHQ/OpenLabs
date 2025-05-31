import uuid
from random import randint


def test_valid_uuid4() -> None:
    """Test we get true for valid uuid4 strings."""
    for _ in range(5):
        test_uuid = uuid.uuid4()
        assert is_valid_uuid4(str(test_uuid))


def test_invalid_uuid4() -> None:
    """Test we get false for invalid uuid4 strings."""
    for _ in range(5):
        invalid_uuid = str(uuid.uuid4())[:-1]
        assert not is_valid_uuid4(invalid_uuid)


def test_wrong_uuid_version_uuid4() -> None:
    """Test that we get false for the wrong UUID version."""
    uuid3_str = str(uuid.uuid1(randint(0, 100), randint(0, 100)))  # noqa: S311
    assert not is_valid_uuid4(uuid3_str)
