def get_api_base_route(version: int) -> str:
    """Return correct API base route URL based on version.

    Args:
    ----
        version (int): API version.

    Returns:
    -------
        str: Base route corresponding to the requested API version.

    """
    if version < 1:
        msg = f"API version cannot be less than 1. Received: {version}"
        raise ValueError(msg)

    api_base_url = "/api"

    if version == 1:
        api_base_url += "/v1"
    else:
        msg = f"Invalid version provided. Received: {version}"
        raise ValueError(msg)

    return api_base_url
