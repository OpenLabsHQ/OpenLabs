import copy

from src.app.schemas.range_schemas import BlueprintRangeSchema
from tests.common.api.v1.config import valid_blueprint_range_create_payload
from tests.test_utils import add_key_recursively, generate_random_int

# Add IDs to simulate a saved blueprint range
valid_blueprint_range_payload = copy.deepcopy(valid_blueprint_range_create_payload)
add_key_recursively(valid_blueprint_range_payload, "id", generate_random_int)

one_all_blueprint = BlueprintRangeSchema.model_validate(
    valid_blueprint_range_payload, from_attributes=True
)
