# RoomMesh

Scan a room with your phone and instantly walk through it in 3D — no waiting, no guesswork, no broken results.

RoomMesh turns ordinary phone video into a navigable, continuous 3D environment. Capture video on an Android phone, stream it to a MacBook for real-time 3D reconstruction using Gaussian Splatting, and immediately view the resulting 3D scene back on the phone. The feedback loop is interactive and self-correcting: users see which areas of a scene are well-covered and which need more footage, catching broken or incomplete scans during capture rather than after.

**Primary use cases:** real estate listings and hotel/short-term rental (Airbnb) previews — prospective guests or buyers can walk through a continuous 3D scan instead of flipping through static photos. An editable mesh export extends this to interior design workflows, where users can repaint walls, swap materials, and experiment with layouts.

## Architecture

```text
Pixel 7 (React Native)
    │
    │  WebRTC (local network)
    │  frames + IMU + ARCore poses
    ▼
MacBook M2 (Python Server)
    ├── WebRTC signaling (FastAPI)
    ├── Online SfM (pycolmap)
    ├── 3DGS optimization (gsplat, MPS backend)
    ├── Mesh extraction + texture baking (SuGaR, optional)
    ├── Scene persistence (local filesystem)
    └── WebGL viewer server (FastAPI static)
    │
    │  HTTP (local network)
    │  .ply scene file + WebGL viewer
    ▼
Pixel 7 (Browser / WebView)
    └── Views the rendered 3D scene
```

The MacBook is a self-contained local processing node — no cloud infrastructure required. The phone and MacBook communicate exclusively over the local network (WebRTC via mDNS, no STUN/TURN needed).

## System Components

- **Mobile Capture Client** (React Native + TypeScript) — captures frames, filters blur/exposure, collects IMU data, gets per-frame ARCore pose priors, and streams everything to the MacBook over WebRTC.
- **MacBook Server** (Python / FastAPI) — handles WebRTC signaling, runs online SfM (`pycolmap`) using ARCore poses as a warm start, optimizes a 3D Gaussian scene (`gsplat` on MPS), and optionally extracts an editable mesh (`SuGaR`).
- **Scene Persistence** — finished scenes are stored as a directory tree on the MacBook's local filesystem (`/scans/scene_NNN/`), each with a `metadata.json`, `scene.ply`, and optional mesh exports. No database required at this stage.
- **Scene Viewer** (WebGL) — the `.ply` file is served alongside an embedded WebGL Gaussian Splatting viewer; the phone opens it in a browser or WebView.

## Data Pipeline

1. **Capture** — phone captures frames, gets ARCore poses, records IMU data, filters/compresses frames, and streams via WebRTC.
2. **Reconstruction** — MacBook runs online SfM (warm-started by ARCore poses) to refine camera poses, then `gsplat` optimizes the 3D Gaussians into `scene.ply`.
3. **Mesh Export** (on demand) — `SuGaR` regularizes the Gaussians to align with physical surfaces, extracts a polygon mesh, and bakes texture, producing `scene_mesh.obj` / `scene_mesh.glb` for use in tools like Blender or Roomle.
4. **Persistence & Serving** — the scene (and any mesh) is written to disk, metadata is updated, and the phone is notified to load the scene from the WebGL viewer.

## Key Technical Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Reconstruction primitive | 3D Gaussian Splatting | Fast, high quality, no dataset needed |
| Reconstruction backend | `gsplat` | MPS support for M2; cleaner than Nerfstudio for production use |
| Mesh extraction | `SuGaR` (on demand) | Produces editable mesh from 3DGS without pretraining |
| SfM approach | Online SfM via `pycolmap` | Real-time pose estimation during capture |
| Compute location | MacBook (local server) | Avoids cloud GPU costs; good fit for M2 hardware |
| Data transport | WebRTC via `aiortc` | Reliable, low latency on local network |
| Mobile framework | React Native (TypeScript) | JS ecosystem, viable ARCore integration via native module |
| Server language | Python | Shared ecosystem with `gsplat`, `pycolmap`, `SuGaR`, `torch` |
| Scene viewing | WebGL viewer served from MacBook | No native Android 3D rendering required |
| Scene persistence | Local filesystem on MacBook | Simple; no database overhead at this stage |

## Open Problems

- **Mobile 3D rendering in React Native** — no native renderer yet; currently sidestepped via the MacBook-served WebGL viewer.
- **Confidence and coverage visualization** — showing which areas of a scan are well-reconstructed is the key feedback-loop feature, and maps to active/ongoing reconstruction research rather than a solved problem.
- **Scene file size** — `.ply` files can run tens to hundreds of MB; compression and resumable transfer will be needed as scenes grow.
- **Mesh quality at room scale** — `SuGaR` output is imperfect for reflective surfaces and complex geometry; a hybrid simplified-room-model approach may prove more practical for interior design workflows.

## Out of Scope (Current Phase)

- Cloud infrastructure or remote reconstruction
- iOS support
- Cross-platform desktop support
- STUN / TURN servers
- Multi-user or collaborative capture
- Business model or monetization

## Full Design Doc

See [docs/3dgs-design-doc.md](docs/3dgs-design-doc.md) for the complete design document, including detailed component responsibilities, library choices, and the WebRTC signaling flow.
