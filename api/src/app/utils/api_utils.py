from fastapi import Response


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


def create_file_download_response(
    content: str | bytes,
    filename: str,
    media_type: str = "text/plain",
) -> Response:
    """Create a FastAPI Response object that triggers a file download.

    Args:
    ----
        content (str | bytes): The content of the file.
        filename (str): The desired filename for the download (e.g., "my-vpn.conf").
        media_type (str): The media (MIME) type of the file.

    Returns:
    -------
        Response: A FastAPI Response object configured for file download.

    """
    # Sanitize the filename to replace spaces, which can cause issues
    safe_filename = filename.replace(" ", "_")

    headers = {"Content-Disposition": f'attachment; filename="{safe_filename}"'}

    return Response(content=content, media_type=media_type, headers=headers)
