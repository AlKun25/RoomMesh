"""WebSocket signaling endpoint for WebRTC SDP/ICE exchange.

This module implements the `/signal` endpoint (issue #5) that establishes the
WebRTC connection between the phone and the MacBook. Signaling runs over a
**WebSocket** rather than plain HTTP: a persistent channel lets us add
renegotiation/reconnect handling in Phase 7 without reworking the transport, and
it carries trickled ICE candidates from the client cleanly.

One WebSocket connection corresponds to one peer connection. The message protocol
(JSON) is:

- client -> server: ``{"type": "offer", "sdp": "<sdp>"}``
- server -> client: ``{"type": "answer", "sdp": "<sdp>"}``
- either way:       ``{"type": "ice-candidate", "candidate": "<cand>",
                        "sdpMid": ..., "sdpMLineIndex": ...}``
- either way:       ``{"type": "bye"}`` (optional clean close)

ICE note: signaling is **non-trickle**. ``aiortc`` only begins ICE connectivity
checks when the remote candidates are present in the offer's SDP — feeding them
after the fact via ``addIceCandidate`` does not start the checks. So the client
gathers its host candidates before sending the offer, and both peers carry their
candidates inside the offer/answer SDP. The ``ice-candidate`` message is still
handled as best-effort forward-compatibility, but is not required for the
handshake. No STUN/TURN is used — phone and MacBook are on the same LAN, so host
candidates are sufficient.
"""

import logging

from aiortc import RTCIceCandidate, RTCPeerConnection, RTCSessionDescription
from aiortc.sdp import candidate_from_sdp
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.config import settings
from src.modules.frames import FrameSink
from src.modules.signaling.connection import PeerConnectionManager

logger = logging.getLogger(__name__)

router = APIRouter()


def _parse_ice_candidate(message: dict) -> RTCIceCandidate | None:
    """Build an ``RTCIceCandidate`` from a client ``ice-candidate`` message.

    The browser/react-native-webrtc candidate string carries a ``candidate:``
    prefix that aiortc's ``candidate_from_sdp`` does not expect. An empty or
    missing candidate signals end-of-gathering and is ignored.
    """
    candidate_str = message.get("candidate")
    if not candidate_str:
        return None

    # react-native-webrtc/browsers prefix the candidate with "candidate:";
    # aiortc's parser expects the value without it.
    if candidate_str.startswith("candidate:"):
        candidate_str = candidate_str[len("candidate:") :]

    candidate = candidate_from_sdp(candidate_str)
    candidate.sdpMid = message.get("sdpMid")
    candidate.sdpMLineIndex = message.get("sdpMLineIndex")
    return candidate


@router.websocket("/signal")
async def signal(websocket: WebSocket) -> None:
    """Exchange SDP offer/answer and ICE candidates over a WebSocket.

    The phone opens the connection, sends its SDP offer, and trickles ICE
    candidates; the server answers and applies the candidates. The peer
    connection is created (and cleaned up) via the shared
    :class:`PeerConnectionManager` stored on ``app.state``.
    """
    # Accept first so a misconfiguration surfaces as a clean close with a reason
    # rather than a bare pre-accept 403 rejection.
    await websocket.accept()

    manager: PeerConnectionManager | None = getattr(websocket.app.state, "peer_connections", None)
    if manager is None:
        logger.error(
            "peer_connections manager missing from app.state; is the app lifespan running?"
        )
        await websocket.close(code=1011, reason="signaling unavailable")
        return

    pc: RTCPeerConnection = manager.create_peer_connection()

    # One capture session per peer connection. The sink is created on the first
    # video track. Its lifetime is tied to the *peer connection*, not this
    # signaling socket — see the teardown note below.
    frame_sink: FrameSink | None = None

    # The client closes the signaling socket as soon as the peer connection is
    # up (signaling is only needed for the handshake); media then flows over the
    # established connection. So once we've answered, a socket close must NOT
    # tear down the pc — otherwise the capture ends the instant it connects.
    # We only clean up here for an *incomplete* handshake (client dropped mid-
    # negotiation) or an explicit ``bye``. Completed sessions are cleaned up when
    # the peer connection reaches a terminal state (below), which also ends the
    # frame sink via its track reaching end-of-stream.
    teardown_on_exit = True

    @pc.on("datachannel")
    def on_datachannel(channel) -> None:
        # The phone opens the data channel; reserved for future control/pose
        # messages. Frames themselves travel over the video track (issue #6).
        logger.info("Data channel opened by client: %s", channel.label)

    @pc.on("track")
    def on_track(track) -> None:
        # The phone streams camera video as a MediaChannel; persist its frames
        # as images for the SfM / 3DGS pipeline (issue #6).
        nonlocal frame_sink
        logger.info("Track received from client: kind=%s", track.kind)
        if track.kind != "video" or frame_sink is not None:
            return
        frame_sink = FrameSink(
            scans_dir=settings.scans_dir,
            save_fps=settings.frame_save_fps,
        )
        frame_sink.start(track)

    @pc.on("connectionstatechange")
    async def on_connectionstatechange() -> None:
        # Finalize the capture session when the peer connection ends (client
        # disconnects, ICE fails). The manager also discards the pc on these
        # states; stopping the sink here is idempotent with its track-end path.
        if pc.connectionState in ("failed", "closed") and frame_sink is not None:
            await frame_sink.stop()

    try:
        while True:
            message = await websocket.receive_json()
            msg_type = message.get("type")

            if msg_type == "offer":
                await pc.setRemoteDescription(
                    RTCSessionDescription(sdp=message["sdp"], type="offer")
                )
                answer = await pc.createAnswer()
                await pc.setLocalDescription(answer)
                # aiortc embeds its gathered ICE candidates in this SDP.
                await websocket.send_json({"type": "answer", "sdp": pc.localDescription.sdp})
                # Handshake done: from here the pc is self-sustaining, so a
                # socket close should leave it (and the capture) running.
                teardown_on_exit = False

            elif msg_type == "ice-candidate":
                candidate = _parse_ice_candidate(message)
                if candidate is not None:
                    await pc.addIceCandidate(candidate)

            elif msg_type == "bye":
                # Explicit client request to close the whole session.
                teardown_on_exit = True
                break

            else:
                logger.warning("Ignoring unknown signaling message: %s", msg_type)

    except WebSocketDisconnect:
        logger.info("Signaling WebSocket disconnected")
    finally:
        # Only tear down on an incomplete handshake or an explicit bye. A
        # completed session keeps streaming over the peer connection after this
        # socket closes; its cleanup runs from on_connectionstatechange.
        if teardown_on_exit:
            if frame_sink is not None:
                await frame_sink.stop()
            if pc.connectionState != "closed":
                await pc.close()
