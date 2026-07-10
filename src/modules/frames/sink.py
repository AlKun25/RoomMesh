"""Persist an incoming WebRTC video track as decimated JPEG frames on disk.

The phone streams camera video over a WebRTC **video track** (a MediaChannel).
aiortc decodes that track into raw frames; :class:`FrameSink` pulls frames off
the track, decimates them to a target rate, and writes each as a JPEG under
``<scans_dir>/<session>/frames/``. A ``metadata.json`` per session records the
capture, mirroring the scene layout in ``docs/3dgs-design-doc.md`` §3.3.

This is the first, byte-lossy pass of the capture pipeline. The eventual
SfM-quality path (byte-exact frames + per-frame ARCore pose over the DataChannel)
plugs in here: it would replace ``track.recv()`` with data-channel frame messages
while keeping the same on-disk contract.
"""

import asyncio
import json
import logging
import time
from datetime import UTC, datetime
from pathlib import Path

from aiortc.mediastreams import MediaStreamError, MediaStreamTrack

logger = logging.getLogger(__name__)


class FrameSink:
    """Consume a video ``MediaStreamTrack`` and store decimated JPEG frames.

    One sink corresponds to one capture session (one video track). Call
    :meth:`start` with the track from ``@pc.on("track")``; call :meth:`stop`
    (idempotent) when the peer connection closes to cancel the reader and
    finalize ``metadata.json``.
    """

    def __init__(
        self,
        scans_dir: str,
        save_fps: float = 4.0,
        session_id: str | None = None,
    ) -> None:
        """Initialize a sink rooted at ``scans_dir``.

        Args:
            scans_dir: Base scans directory (``settings.scans_dir``).
            save_fps: Target frames-per-second to persist; incoming frames are
                decimated to at most this rate by arrival time.
            session_id: Optional explicit session id; defaults to a UTC
                timestamp so concurrent/sequential captures never collide.
        """
        self.save_fps = save_fps
        self._min_interval = 1.0 / save_fps if save_fps > 0 else 0.0
        self._session_id = session_id or datetime.now(UTC).strftime(
            "session_%Y%m%dT%H%M%S_%f"
        )
        self._session_dir = Path(scans_dir) / self._session_id
        self._frames_dir = self._session_dir / "frames"

        self._task: asyncio.Task | None = None
        self._started_at: str | None = None
        self._frame_count = 0
        self._width: int | None = None
        self._height: int | None = None
        self._stopped = False

    @property
    def session_id(self) -> str:
        """The session identifier (and directory name) for this capture."""
        return self._session_id

    @property
    def session_dir(self) -> Path:
        """Absolute-or-relative path to this session's directory."""
        return self._session_dir

    @property
    def frame_count(self) -> int:
        """Number of frames written to disk so far."""
        return self._frame_count

    def start(self, track: MediaStreamTrack) -> None:
        """Begin reading ``track`` in a background task.

        Creates the session directory, writes an initial ``metadata.json``, and
        schedules the frame-reader coroutine. Safe to call once per sink.
        """
        if self._task is not None:
            logger.warning("FrameSink already started for %s", self._session_id)
            return

        self._frames_dir.mkdir(parents=True, exist_ok=True)
        self._started_at = datetime.now(UTC).isoformat()
        self._write_metadata(status="capturing")
        logger.info("Frame capture started: %s", self._session_dir)

        self._task = asyncio.ensure_future(self._run(track))

    async def _run(self, track: MediaStreamTrack) -> None:
        """Pull frames until the track ends, saving at the target rate."""
        last_saved = 0.0
        try:
            while True:
                frame = await track.recv()

                now = time.monotonic()
                # Always save the first frame; then decimate by arrival time.
                if self._frame_count > 0 and (now - last_saved) < self._min_interval:
                    continue
                last_saved = now

                self._save_frame(frame)
        except MediaStreamError:
            # Track ended (peer closed / disconnected) — normal termination.
            logger.info("Video track ended for %s", self._session_id)
        except asyncio.CancelledError:
            logger.info("Frame capture cancelled for %s", self._session_id)
            raise
        except Exception:  # pragma: no cover - defensive
            logger.exception("Frame capture failed for %s", self._session_id)
        finally:
            self._write_metadata(status="complete", finished=True)
            logger.info(
                "Frame capture finished: %s (%d frames)",
                self._session_dir,
                self._frame_count,
            )

    def _save_frame(self, frame) -> None:
        """Encode one decoded video frame to a numbered JPEG."""
        image = frame.to_image()  # PIL.Image (requires Pillow); av does the decode
        if self._width is None:
            self._width, self._height = image.width, image.height
        self._frame_count += 1
        path = self._frames_dir / f"frame_{self._frame_count:05d}.jpg"
        image.save(path, format="JPEG", quality=90)

    def _write_metadata(self, status: str, finished: bool = False) -> None:
        """Write/refresh ``metadata.json`` for the session."""
        metadata = {
            "session_id": self._session_id,
            "started_at": self._started_at,
            "finished_at": datetime.now(UTC).isoformat() if finished else None,
            "status": status,
            "frame_count": self._frame_count,
            "width": self._width,
            "height": self._height,
            "save_fps": self.save_fps,
        }
        (self._session_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))

    async def stop(self) -> None:
        """Cancel the reader (if running) and finalize metadata. Idempotent."""
        if self._stopped:
            return
        self._stopped = True

        if self._task is not None and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
