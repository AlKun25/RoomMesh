"""Incoming media-frame ingestion and on-disk storage.

This package consumes the WebRTC **video track** the phone sends and persists
decimated frames as JPEG images under the scans directory, ready for the online
SfM → 3D Gaussian Splatting pipeline (see ``docs/3dgs-design-doc.md``).
"""

from src.modules.frames.sink import FrameSink

__all__ = ["FrameSink"]
