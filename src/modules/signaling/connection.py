"""WebRTC peer-connection management via aiortc.

This module owns the server-side `RTCPeerConnection` lifecycle. It deliberately
does **not** handle signaling transport (SDP offer/answer exchange over an HTTP
endpoint) — that is added in a later issue. Its job here is to construct peer
connections with **no audio track** and keep track of them so they can be closed
cleanly on application shutdown.
"""

import logging

from aiortc import RTCDataChannel, RTCPeerConnection

logger = logging.getLogger(__name__)


class PeerConnectionManager:
    """Create and track WebRTC peer connections, audio-free.

    RoomMesh only needs a data (and later video) path from the phone to the
    MacBook, so connections are created without any audio transceiver. The
    manager keeps a registry of open connections and closes them all on
    shutdown, mirroring how ``BonjourAdvertiser`` is torn down in the app
    lifespan.
    """

    def __init__(self) -> None:
        """Initialize an empty peer-connection registry."""
        self._connections: set[RTCPeerConnection] = set()

    def create_peer_connection(self) -> RTCPeerConnection:
        """Create and register an audio-free ``RTCPeerConnection``.

        No audio track or transceiver is added. The connection is removed from
        the registry automatically when it reaches a terminal connection state.

        Returns:
            RTCPeerConnection: A newly created, tracked peer connection.
        """
        pc = RTCPeerConnection()
        self._connections.add(pc)

        @pc.on("connectionstatechange")
        async def on_connectionstatechange() -> None:
            logger.info("Peer connection state -> %s", pc.connectionState)
            if pc.connectionState in ("failed", "closed"):
                await self._discard(pc)

        return pc

    def create_data_channel(self, pc: RTCPeerConnection, label: str = "roommesh") -> RTCDataChannel:
        """Create a data channel on ``pc``.

        Data channels are codec-agnostic (SCTP), so this path involves no media
        codec negotiation between aiortc and react-native-webrtc.

        Args:
            pc: The peer connection to open the channel on.
            label: Data-channel label.

        Returns:
            RTCDataChannel: The created data channel.
        """
        return pc.createDataChannel(label)

    async def _discard(self, pc: RTCPeerConnection) -> None:
        """Close ``pc`` (if needed) and drop it from the registry."""
        self._connections.discard(pc)
        if pc.connectionState != "closed":
            await pc.close()

    async def close_all(self) -> None:
        """Close every tracked peer connection.

        Called from the application lifespan shutdown block.
        """
        connections = list(self._connections)
        self._connections.clear()
        for pc in connections:
            if pc.connectionState != "closed":
                await pc.close()
        logger.info("Closed %d peer connection(s)", len(connections))

    @property
    def connection_count(self) -> int:
        """Number of currently tracked peer connections."""
        return len(self._connections)
