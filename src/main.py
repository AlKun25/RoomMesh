"""RoomMesh FastAPI application."""

import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from src.config import settings
from src.modules.discovery import BonjourAdvertiser
from src.modules.health import routes as health_routes
from src.modules.signaling import PeerConnectionManager

logger = logging.getLogger(__name__)

bonjour: BonjourAdvertiser | None = None
peer_connections: PeerConnectionManager | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle (startup and shutdown)."""
    global bonjour, peer_connections
    # Startup
    bonjour = BonjourAdvertiser(
        service_name=settings.mdns_service_name,
        port=settings.port,
        host=settings.host,
        enable=settings.mdns_enabled,
    )
    bonjour.start()
    peer_connections = PeerConnectionManager()
    yield
    # Shutdown
    if bonjour:
        bonjour.stop()
    if peer_connections:
        await peer_connections.close_all()


app = FastAPI(
    title="RoomMesh",
    description="A room/mesh networking solution",
    lifespan=lifespan,
)

app.include_router(health_routes.router)


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
