"""End-to-end tests for the ``/signal`` WebSocket signaling endpoint (issue #5).

These tests prove the SDP offer/answer exchange and ICE handling establish a real
WebRTC connection over the WebSocket transport. A live ``uvicorn`` server is run in
a background thread and an ``aiortc`` peer connection plays the role of the phone:
it opens the ``/signal`` socket, sends its offer, applies the server's answer, and
the two peers connect over LAN host candidates (no STUN/TURN).

Starlette's ``TestClient.websocket_connect`` is synchronous, which does not compose
with the async ``aiortc`` peer, so a genuinely live server is used instead.
"""

import asyncio
import json
import socket
import threading
import time

import pytest
import uvicorn
import websockets
from aiortc import RTCPeerConnection, RTCSessionDescription

from src.config import settings
from src.main import app
from src.modules.signaling.routes import _parse_ice_candidate


def _free_port() -> int:
    """Return an unused TCP port on the loopback interface."""
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


class _ThreadedUvicornServer(uvicorn.Server):
    """A uvicorn server that skips signal handlers so it can run off-thread."""

    def install_signal_handlers(self) -> None:
        pass


@pytest.fixture
def live_server():
    """Run the FastAPI app on a background thread and yield its port.

    mDNS advertising is disabled for the duration so the test does not touch the
    network beyond loopback.
    """
    original_mdns = settings.mdns_enabled
    settings.mdns_enabled = False

    port = _free_port()
    config = uvicorn.Config(
        app, host="127.0.0.1", port=port, log_level="warning", lifespan="on"
    )
    server = _ThreadedUvicornServer(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    deadline = time.monotonic() + 10
    while not server.started:
        if time.monotonic() > deadline:
            raise RuntimeError("uvicorn test server failed to start")
        time.sleep(0.05)

    try:
        yield port
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        settings.mdns_enabled = original_mdns


class TestIceCandidateParsing:
    """Unit tests for the client-trickled ICE candidate parser."""

    def test_parses_prefixed_candidate(self) -> None:
        """A browser-style ``candidate:`` string is parsed with its mid/index."""
        candidate = _parse_ice_candidate(
            {
                "candidate": "candidate:1 1 udp 2130706431 192.168.1.5 54321 typ host",
                "sdpMid": "0",
                "sdpMLineIndex": 0,
            }
        )
        assert candidate is not None
        assert candidate.ip == "192.168.1.5"
        assert candidate.port == 54321
        assert candidate.sdpMid == "0"
        assert candidate.sdpMLineIndex == 0

    def test_empty_candidate_is_ignored(self) -> None:
        """An empty candidate (end-of-gathering) yields ``None``."""
        assert _parse_ice_candidate({"candidate": ""}) is None
        assert _parse_ice_candidate({}) is None


class TestSignalingHandshake:
    """Live WebSocket handshake between an aiortc 'phone' and the server."""

    async def test_handshake_establishes_data_only_connection(
        self, live_server: int
    ) -> None:
        """Offer/answer over ``/signal`` reaches ``connected`` with no audio track."""
        port = live_server
        phone = RTCPeerConnection()
        channel = phone.createDataChannel("roommesh")

        channel_open = asyncio.Event()
        channel.on("open", channel_open.set)

        connected = asyncio.Event()

        @phone.on("connectionstatechange")
        async def _on_state() -> None:
            if phone.connectionState == "connected":
                connected.set()

        try:
            async with websockets.connect(f"ws://127.0.0.1:{port}/signal") as ws:
                offer = await phone.createOffer()
                await phone.setLocalDescription(offer)
                # aiortc embeds its gathered host candidates in this offer SDP.
                await ws.send(
                    json.dumps(
                        {"type": "offer", "sdp": phone.localDescription.sdp}
                    )
                )

                # Await the server's SDP answer (its candidates ride inside it).
                while True:
                    raw = await asyncio.wait_for(ws.recv(), timeout=10)
                    message = json.loads(raw)
                    if message["type"] == "answer":
                        await phone.setRemoteDescription(
                            RTCSessionDescription(
                                sdp=message["sdp"], type="answer"
                            )
                        )
                        break

                await asyncio.wait_for(connected.wait(), timeout=15)
                await asyncio.wait_for(channel_open.wait(), timeout=15)

                # Acceptance criteria: connection established, no audio track.
                assert phone.connectionState == "connected"
                assert "m=audio" not in phone.localDescription.sdp
                assert "m=audio" not in phone.remoteDescription.sdp
        finally:
            await phone.close()
