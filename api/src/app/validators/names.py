_ALPHA_RANGE = r"A-Za-z"
_NUMERIC_RANGE = r"0-9"

# Provider users flexibility in their naming conventions
NAME_DELIMITERS = r" _\-"

NAME_START_CHAR = _ALPHA_RANGE
NAME_BODY_CHARS = _ALPHA_RANGE + _NUMERIC_RANGE + NAME_DELIMITERS
NAME_END_CHAR = _ALPHA_RANGE + _NUMERIC_RANGE

# MAX_LENGTH = 64
# This was chosen as a good round number.
#
# MIN_LENGTH = 3
# This is to enforce readability in labs
OPENLABS_NAME_REGEX = (
    rf"^[{NAME_START_CHAR}][{NAME_BODY_CHARS}]{{1,62}}[{NAME_END_CHAR}]$"
)
