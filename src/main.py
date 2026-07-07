"""RoomMesh FastAPI application."""

import uvicorn
from fastapi import FastAPI

from src.config import settings
from src.modules.health import routes as health_routes

app = FastAPI(
    title="RoomMesh",
    description="A room/mesh networking solution",
)

app.include_router(health_routes.router)


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
