"""Tests for the WebRTC signaling / peer-connection scaffolding.

These tests prove the aiortc peer connection forms with a data channel and
**no audio track**, satisfying issue #4's acceptance criteria at the library
level (a real phone<->MacBook handshake over an HTTP signaling endpoint is
issue #5). Two in-process ``RTCPeerConnection``s are wired together by passing
the SDP offer/answer directly, with no network involved.
"""

import asyncio

from aiortc import RTCPeerConnection, RTCSessionDescription

from src.modules.signaling import PeerConnectionManager


async def _wait_for(predicate, timeout: float = 5.0) -> None:
    """Poll ``predicate`` until true or ``timeout`` seconds elapse."""
    loop = asyncio.get_event_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        if predicate():
            return
        await asyncio.sleep(0.05)
    raise AssertionError("Condition not met within timeout")


class TestPeerConnectionManager:
    """Unit tests for PeerConnectionManager."""

    async def test_creates_and_tracks_connection(self) -> None:
        """A created peer connection is registered in the manager."""
        manager = PeerConnectionManager()
        pc = manager.create_peer_connection()

        assert isinstance(pc, RTCPeerConnection)
        assert manager.connection_count == 1

        await manager.close_all()

    async def test_offer_has_no_audio(self) -> None:
        """The offer generated for a data-only connection has no audio media."""
        manager = PeerConnectionManager()
        pc = manager.create_peer_connection()
        manager.create_data_channel(pc)

        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)

        assert "m=audio" not in pc.localDescription.sdp
        # No audio sender/receiver should exist on the connection.
        assert all(
            t.kind != "audio" for t in pc.getTransceivers()
        )

        await manager.close_all()

    async def test_close_all_closes_connections(self) -> None:
        """close_all() closes every tracked connection and empties the registry."""
        manager = PeerConnectionManager()
        pc1 = manager.create_peer_connection()
        pc2 = manager.create_peer_connection()
        assert manager.connection_count == 2

        await manager.close_all()

        assert manager.connection_count == 0
        assert pc1.connectionState == "closed"
        assert pc2.connectionState == "closed"


class TestLoopbackConnection:
    """End-to-end (in-process) peer-connection establishment test."""

    async def test_data_only_peer_connection_establishes_without_audio(self) -> None:
        """Two peers connect via a data channel with no audio track present.

        Wires an offerer to an answerer by exchanging SDP directly (no network,
        no signaling server) and confirms the connection reaches "connected"
        and that neither negotiated description contains an audio media line.
        """
        manager = PeerConnectionManager()
        offerer = manager.create_peer_connection()
        answerer = RTCPeerConnection()

        connected = {"offerer": False, "answerer": False}

        @offerer.on("connectionstatechange")
        async def _on_offerer_state() -> None:
            if offerer.connectionState == "connected":
                connected["offerer"] = True

        @answerer.on("connectionstatechange")
        async def _on_answerer_state() -> None:
            if answerer.connectionState == "connected":
                connected["answerer"] = True

        channel_open = asyncio.Event()
        manager.create_data_channel(offerer, label="roommesh").on(
            "open", channel_open.set
        )

        try:
            # Offer/answer exchange (direct, in-process).
            offer = await offerer.createOffer()
            await offerer.setLocalDescription(offer)
            await answerer.setRemoteDescription(
                RTCSessionDescription(
                    sdp=offerer.localDescription.sdp,
                    type=offerer.localDescription.type,
                )
            )
            answer = await answerer.createAnswer()
            await answerer.setLocalDescription(answer)
            await offerer.setRemoteDescription(
                RTCSessionDescription(
                    sdp=answerer.localDescription.sdp,
                    type=answerer.localDescription.type,
                )
            )

            await _wait_for(lambda: connected["offerer"] and connected["answerer"])
            await _wait_for(channel_open.is_set)

            # Acceptance criteria: connection established, no audio track.
            assert offerer.connectionState == "connected"
            assert answerer.connectionState == "connected"
            assert "m=audio" not in offerer.localDescription.sdp
            assert "m=audio" not in answerer.localDescription.sdp
        finally:
            await manager.close_all()
            await answerer.close()
