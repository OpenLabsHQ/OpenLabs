_ALPHA_RANGE = r"A-Za-z"
_NUMERIC_RANGE = r"0-9"

# Provider user's flexibility in their naming conventions
NAME_DELIMETERS = r" _\-"

NAME_START_CHAR = _ALPHA_RANGE
NAME_BODY_CHARS = _ALPHA_RANGE + _NUMERIC_RANGE + NAME_DELIMETERS
NAME_END_CHAR = _ALPHA_RANGE + _NUMERIC_RANGE

# MAX_LENGTH = 64
# This was choosen as a good round number.
#
# MIN_LENGTH = 3
# This is to enforce readability in labs
OPENLABS_NAME_REGEX = (
    rf"^[{NAME_START_CHAR}][{NAME_BODY_CHARS}]{{1,62}}[{NAME_END_CHAR}]$"
)
