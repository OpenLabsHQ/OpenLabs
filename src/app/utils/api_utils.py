def get_api_base_route(version: int) -> str:
    """Return correct API base route URL based on version."""
    if version < 1:
        msg = f"API version cannot be less than 1. Recieved: {version}"
        raise ValueError(msg)

    api_base_url = "/api"

    if version == 1:
        api_base_url += "/v1"
    else:
        msg = f"Invalid version provided. Recieved: {version}"
        raise ValueError(msg)

    return api_base_url
