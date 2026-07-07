"""Health check endpoint routes."""

from datetime import UTC, datetime

from fastapi import APIRouter

import src

router = APIRouter()


@router.get("/health")
async def health_check():
    """Get application health status.

    Returns:
        dict: Health status with timestamp and version.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "version": src.__version__,
    }
