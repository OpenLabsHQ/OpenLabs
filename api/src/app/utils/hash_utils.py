import uuid

# Base36 alphabet are safest for resource naming across cloud providers
# 0-9 (10) + a-z (26) = 36 characters
BASE36_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz"


def base36_encode(number: int) -> str:
    """Encode a non-negative integer into a Base36 string.

    Args:
        number: The non-negative integer to encode.

    Returns:
        The Base36 encoded string representation of the number.

    Raises:
        ValueError: If the input number is negative.

    """
    if number < 0:
        msg = "Cannot encode negative numbers. Input must be non-negative."
        raise ValueError(msg)

    if number == 0:
        return BASE36_ALPHABET[0]

    base = len(BASE36_ALPHABET)
    encoded_chars = []

    # Use divmod for efficiency
    while number > 0:
        number, remainder = divmod(number, base)
        encoded_chars.append(BASE36_ALPHABET[remainder])

    # Chars are generated from right to left
    return "".join(reversed(encoded_chars))


def generate_short_hash(
    uuid_obj: uuid.UUID | None = None,
) -> str:
    """Generate a short collision resistant hash from a UUID object.

    This takes the integer value of a uuid object and then codes

    Args:
        uuid_obj: An optional UUID object to be encoded.


    Returns:
        A short Base36 hash string.

    """
    if uuid_obj is None:
        uuid_obj = uuid.uuid4()

    return base36_encode(uuid_obj.int)
