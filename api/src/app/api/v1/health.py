from fastapi import APIRouter

router = APIRouter(prefix="/health")


@router.get("/ping", tags=["health"])
async def ping_check() -> dict[str, str]:
    """Ping the API server.

    Returns
    -------
        dict[str, str]: Dictionary with message 'pong'.

    """
    return {"msg": "pong"}
