"""Tests for video-frame ingestion and on-disk storage (issue #6).

Two layers:

- Unit tests drive :class:`FrameSink` directly with a fake track, covering the
  save/decimate/metadata logic without any networking.
- One integration test runs the live ``/signal`` server (same harness as
  ``test_signaling_route.py``) with an aiortc "phone" that adds a synthetic video
  track, and asserts the server persists JPEG frames + ``metadata.json`` under a
  temp scans directory.
"""

import asyncio
import json
import socket
import threading
import time

import av
import pytest
import uvicorn
import websockets
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.mediastreams import MediaStreamError, MediaStreamTrack, VideoStreamTrack

from src.config import settings
from src.main import app
from src.modules.frames import FrameSink


def _black_frame(width: int = 64, height: int = 48) -> av.VideoFrame:
    """Build a decodable all-zero YUV frame for tests."""
    frame = av.VideoFrame(width=width, height=height)
    for plane in frame.planes:
        plane.update(bytes(plane.buffer_size))
    return frame


class _FakeTrack(MediaStreamTrack):
    """A video track that yields ``count`` frames then ends the stream."""

    kind = "video"

    def __init__(self, count: int) -> None:
        super().__init__()
        self._remaining = count

    async def recv(self) -> av.VideoFrame:
        if self._remaining <= 0:
            raise MediaStreamError
        self._remaining -= 1
        return _black_frame()


class TestFrameSink:
    """Unit tests for the frame-storage sink."""

    async def test_saves_frames_and_metadata(self, tmp_path) -> None:
        """Every frame is written when the save rate is not the bottleneck."""
        # A very high save rate means no decimation, so all frames land on disk.
        sink = FrameSink(scans_dir=str(tmp_path), save_fps=10_000, session_id="s1")
        sink.start(_FakeTrack(count=5))
        await sink._task  # run the reader to completion (track ends)

        frames_dir = tmp_path / "s1" / "frames"
        saved = sorted(frames_dir.glob("*.jpg"))
        assert len(saved) == 5
        assert [p.name for p in saved][:2] == ["frame_00001.jpg", "frame_00002.jpg"]

        metadata = json.loads((tmp_path / "s1" / "metadata.json").read_text())
        assert metadata["frame_count"] == 5
        assert metadata["status"] == "complete"
        assert metadata["finished_at"] is not None
        assert metadata["width"] == 64 and metadata["height"] == 48

    async def test_decimates_by_rate(self, tmp_path) -> None:
        """Frames arriving faster than the save rate are dropped."""
        # save_fps=2 -> min 0.5s between saves; all 5 frames arrive near-instantly,
        # so only the first survives.
        sink = FrameSink(scans_dir=str(tmp_path), save_fps=2, session_id="s2")
        sink.start(_FakeTrack(count=5))
        await sink._task

        saved = list((tmp_path / "s2" / "frames").glob("*.jpg"))
        assert len(saved) == 1

    async def test_stop_is_idempotent(self, tmp_path) -> None:
        """Calling stop after natural completion is safe."""
        sink = FrameSink(scans_dir=str(tmp_path), save_fps=10_000, session_id="s3")
        sink.start(_FakeTrack(count=1))
        await sink._task
        await sink.stop()
        await sink.stop()
        assert sink.frame_count == 1


# --- Integration: real peer connection streaming a synthetic video track -------


def _free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


class _ThreadedUvicornServer(uvicorn.Server):
    def install_signal_handlers(self) -> None:
        pass


class _DummyVideoTrack(VideoStreamTrack):
    """Emits paced black frames so the server has something to persist."""

    async def recv(self) -> av.VideoFrame:
        pts, time_base = await self.next_timestamp()
        frame = _black_frame(width=320, height=240)
        frame.pts = pts
        frame.time_base = time_base
        return frame


@pytest.fixture
def live_server(tmp_path):
    """Run the app on a background thread, storing frames under tmp_path."""
    original_mdns = settings.mdns_enabled
    original_scans = settings.scans_dir
    original_fps = settings.frame_save_fps
    settings.mdns_enabled = False
    settings.scans_dir = str(tmp_path)
    settings.frame_save_fps = 10  # enough frames within a short stream

    port = _free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", lifespan="on")
    server = _ThreadedUvicornServer(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    deadline = time.monotonic() + 10
    while not server.started:
        if time.monotonic() > deadline:
            raise RuntimeError("uvicorn test server failed to start")
        time.sleep(0.05)

    try:
        yield port, tmp_path
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        settings.mdns_enabled = original_mdns
        settings.scans_dir = original_scans
        settings.frame_save_fps = original_fps


class TestVideoStreamPersistence:
    """The server stores frames from a streamed video track."""

    async def test_streamed_frames_are_saved(self, live_server) -> None:
        """A video track over ``/signal`` produces JPEG frames on disk.

        Critically, this mirrors the real client: it **closes the signaling
        socket as soon as the answer is applied** (the phone does this once the
        peer link is up). Frames must still flow over the surviving peer
        connection — a regression here means the server tore the pc down when the
        signaling socket closed.
        """
        port, scans_dir = live_server
        phone = RTCPeerConnection()
        phone.addTrack(_DummyVideoTrack())

        connected = asyncio.Event()

        @phone.on("connectionstatechange")
        async def _on_state() -> None:
            if phone.connectionState == "connected":
                connected.set()

        try:
            # Signaling handshake, then close the socket like the real client.
            async with websockets.connect(f"ws://127.0.0.1:{port}/signal") as ws:
                offer = await phone.createOffer()
                await phone.setLocalDescription(offer)
                assert "m=video" in phone.localDescription.sdp
                await ws.send(json.dumps({"type": "offer", "sdp": phone.localDescription.sdp}))

                while True:
                    raw = await asyncio.wait_for(ws.recv(), timeout=10)
                    message = json.loads(raw)
                    if message["type"] == "answer":
                        await phone.setRemoteDescription(
                            RTCSessionDescription(sdp=message["sdp"], type="answer")
                        )
                        break
            # ^ signaling socket now closed; media continues over the pc.

            await asyncio.wait_for(connected.wait(), timeout=15)

            # Let frames flow over the still-open peer connection, then poll.
            deadline = time.monotonic() + 10
            saved: list = []
            while time.monotonic() < deadline:
                saved = list(scans_dir.glob("*/frames/*.jpg"))
                if saved:
                    break
                await asyncio.sleep(0.2)

            assert saved, "no frames were persisted after the signaling socket closed"
        finally:
            await phone.close()

        # The session's metadata.json is written once the connection tears down.
        deadline = time.monotonic() + 5
        metadata_files: list = []
        while time.monotonic() < deadline:
            metadata_files = list(scans_dir.glob("*/metadata.json"))
            if metadata_files:
                break
            await asyncio.sleep(0.2)
        assert metadata_files, "metadata.json was not written"
        metadata = json.loads(metadata_files[0].read_text())
        assert metadata["frame_count"] >= 1
