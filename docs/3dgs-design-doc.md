# 3D Gaussian Splatting Capture System: Design Document

> An app that turns ordinary phone video into a navigable, continuous 3D environment.

---

## 1. Product Vision

The system allows a user to capture video on their Android phone, stream it to a MacBook for real-time 3D reconstruction using Gaussian Splatting, and immediately view the resulting 3D scene on their phone. The feedback loop is interactive and self-correcting: the user sees which areas of the scene are well-covered and which need more footage, so broken or incomplete scans are caught during capture rather than after.

**Primary use cases:** real estate listings, hotel and short-term rental (Airbnb) previews. Prospective guests or buyers can walk through a continuous 3D scan instead of flipping through static photos. The editable mesh export extends this to interior design workflows where users can repaint walls, swap materials, and experiment with layouts.

**One-liner:** Scan a room with your phone and instantly walk through it in 3D, with no waiting, no guesswork, and no broken results.

---

## 2. High-Level Architecture

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

The MacBook acts as a self-contained local processing node. No cloud infrastructure is required. The phone and MacBook communicate exclusively over the local network.

---

## 3. System Components

### 3.1 Mobile Capture Client (React Native + TypeScript)

Responsible for capturing and preprocessing data before sending it to the MacBook.

**Pre-computation on device (Pixel 7):**

| Task                                | Purpose                                                                           |
| ----------------------------------- | --------------------------------------------------------------------------------- |
| Frame decimation                    | Drop redundant frames before sending; avoids streaming unnecessary data           |
| Blur detection (Laplacian variance) | Filter motion-blurred frames that would degrade SfM                               |
| Exposure check                      | Reject over or underexposed frames                                                |
| IMU collection                      | Accelerometer and gyroscope timestamps alongside frames; warms up pose estimation |
| ARCore pose estimation              | Per-frame camera pose priors; dramatically reduces MacBook SfM workload           |
| JPEG / WebP compression             | Reduce frame size before WebRTC transmission                                      |

ARCore poses are the most valuable pre-computation. They are noisy and drift over time but serve as a strong warm start for the online SfM running on the MacBook.

**Key libraries:**

| Library                      | Role                                              |
| ---------------------------- | ------------------------------------------------- |
| `react-native-webrtc`        | WebRTC data pipe to MacBook                       |
| `react-native-vision-camera` | Camera control (exposure, focus lock, frame rate) |
| ARCore native module         | Per-frame pose data                               |
| `react-native-sensors`       | IMU data                                          |

### 3.2 MacBook Server (Python)

The MacBook is the single server. It handles signaling, reconstruction, mesh export, persistence, and scene serving.

**Responsibilities:**

- WebRTC signaling via a FastAPI endpoint
- Receiving frames, IMU data, and ARCore poses
- Running online SfM to produce refined camera poses
- Running gsplat to optimize the 3D Gaussian scene
- Running SuGaR on demand to extract an editable mesh
- Persisting finished scenes to the local filesystem
- Serving the scene file and WebGL viewer to the phone

**Key libraries:**

| Library               | Role                                                 |
| --------------------- | ---------------------------------------------------- |
| `fastapi` + `uvicorn` | Web server and REST API                              |
| `aiortc`              | WebRTC implementation                                |
| `gsplat`              | 3D Gaussian Splatting optimization                   |
| `pycolmap`            | Online Structure from Motion                         |
| `SuGaR`               | Surface mesh extraction and texture baking from 3DGS |
| `torch` (MPS backend) | GPU compute on M2 via Metal Performance Shaders      |
| `open3d`              | Point cloud handling                                 |
| `numpy`               | Compute foundation                                   |

### 3.3 Scene Persistence (Local Filesystem)

Scenes are stored as a structured directory tree on the MacBook.

```text
/scans
  /scene_001
    /frames
    poses.json
    scene.ply
    scene_mesh.obj      # present only if SuGaR export was requested
    scene_mesh.glb      # present only if SuGaR export was requested
    metadata.json
  /scene_002
    ...
```

A `metadata.json` per scene tracks job status, timestamps, and whether a mesh export has been generated. No database is needed at this stage. The FastAPI server indexes the `/scans` directory and exposes scene listings and file access over the local network.

### 3.4 Scene Viewer (WebGL, served from MacBook)

The finished `.ply` file is served alongside an embedded WebGL Gaussian Splatting viewer hosted by FastAPI. The phone opens a URL such as `macbook.local:8000/scenes/scene_001` in the browser or a WebView inside the React Native app.

Candidate viewers: antimatter15's WebGL splat viewer or Niantic's open-source Scaniverse web viewer. Both are embeddable and require no native Android rendering code.

---

## 4. Data Pipeline

### 4.1 Capture Phase

```text
Pixel 7
  └── react-native-vision-camera captures frames
  └── ARCore produces per-frame pose estimate
  └── IMU records accelerometer + gyro timestamps
  └── Frame preprocessor (blur check, exposure check, decimation, compression)
  └── react-native-webrtc streams frames + poses + IMU to MacBook
```

### 4.2 Reconstruction Phase

```text
MacBook
  └── aiortc receives frame stream
  └── pycolmap runs online SfM
       └── Uses ARCore poses as warm start
       └── Produces refined camera poses + sparse point cloud
  └── gsplat optimizes 3D Gaussians from posed frames
       └── Runs on M2 GPU via MPS backend
  └── Output: scene.ply
```

### 4.3 Mesh Export Phase (On Demand)

This phase is optional and triggered explicitly by the user when they want an editable 3D model, for example for interior design work.

```text
MacBook
  └── SuGaR takes scene.ply + original posed frames as input
  └── Runs surface-regularized Gaussian optimization
       └── Encourages Gaussians to align with physical surfaces
  └── Extracts a polygon mesh from the regularized Gaussians
  └── Bakes photorealistic texture from the Gaussian colors onto the mesh
  └── Output: scene_mesh.obj + scene_mesh.glb
```

The resulting `.obj` or `.glb` file is a standard 3D mesh that can be imported into Blender, Roomle, or any interior design tool. Walls, floors, and ceilings become actual surfaces that can be repainted or retextured. SuGaR requires no pretraining on external data; it is a per-scene optimization just like gsplat.

The tradeoff is time. SuGaR takes meaningfully longer than vanilla gsplat because of the additional regularization and mesh extraction passes. For this reason it runs as a separate on-demand step rather than replacing the fast gsplat preview.

### 4.4 Persistence and Serving Phase

```text
MacBook
  └── scene.ply (and optionally mesh files) written to /scans/scene_NNN/
  └── metadata.json updated with completion status
  └── FastAPI notifies mobile client that scene is ready
  └── Phone opens macbook.local:8000/scenes/scene_NNN
  └── WebGL viewer loads and renders scene.ply
```

---

## 5. WebRTC Design

Because the phone and MacBook communicate over a local network, STUN and TURN servers are not needed. The signaling flow is:

1. React Native app connects to `macbook.local:8000/signal`
2. SDP offer and answer are exchanged over HTTP
3. A DataChannel or MediaChannel opens over the local network
4. Frames, poses, and IMU data begin flowing

The MacBook needs a stable local address. Using mDNS (`macbook.local`) is the cleanest approach and avoids hardcoding IP addresses.

---

## 6. Reconstruction Primitive

**3D Gaussian Splatting (3DGS)** is the chosen primitive.

| Property               | Detail                                                  |
| ---------------------- | ------------------------------------------------------- |
| Training time          | Minutes per scene (vs. hours for NeRF)                  |
| Render speed           | 100+ fps on consumer hardware                           |
| Indoor quality         | Strong; better than NeRF for bounded indoor scenes      |
| Training data required | None; per-scene optimization with no pretrained weights |
| Compute backend        | gsplat with PyTorch MPS on M2                           |

3DGS does not require a dataset of prior scenes. Given posed frames of a specific room, it optimizes a set of 3D Gaussians from scratch to represent that room. The only prerequisite is accurate camera poses, which the online SfM pipeline provides.

---

## 7. Mesh Extraction via SuGaR

Standard 3DGS produces a radiance field representation, not a mesh. The `.ply` output is a cloud of millions of tiny Gaussians that looks photorealistic when rendered but has no concept of surfaces, walls, or objects in the traditional 3D sense.

SuGaR (Surface Gaussian Reconstruction) bridges this gap. During optimization it adds a regularization term that encourages Gaussians to flatten and align with physical surfaces. After optimization it extracts a clean polygon mesh and bakes the Gaussian colors onto it as a texture.

**Why this matters for the product:** the exported mesh can be imported into any standard 3D tool (Blender, Roomle, Planner 5D). Walls become paintable surfaces. Materials become swappable. This opens the product to interior design use cases beyond simple 3D previewing.

**Known limitations of mesh extraction at room scale:**

- Windows, mirrors, and reflective surfaces confuse both reconstruction and mesh extraction
- Furniture with thin legs or complex geometry produces noisier meshes
- Large flat surfaces (walls, floors, ceilings) extract cleanly

The mesh will be usable but imperfect relative to a professionally modeled architectural drawing. For the interior design use case, a hybrid approach may eventually be more practical: use the 3DGS scene as a photorealistic backdrop and overlay a simplified editable room model (flat planes for walls, floor, and ceiling) fitted to the scan geometry.

---

## 8. Online SfM Role

Structure from Motion is a prerequisite step, not an optional one. Before gsplat can place Gaussians in 3D space it needs to know where the camera was at every frame.

The online SfM pipeline (pycolmap) takes incoming frames and ARCore pose priors and produces refined camera poses plus a sparse point cloud. ARCore poses serve as a warm start, which makes the SfM faster and more stable. The output feeds directly into gsplat.

This runs continuously on the MacBook during capture, enabling the eventual feedback loop where the user can see which areas of the scene are well-reconstructed and which need more coverage.

---

## 9. Key Technical Decisions

| Decision                 | Choice                           | Rationale                                                      |
| ------------------------ | -------------------------------- | -------------------------------------------------------------- |
| Reconstruction primitive | 3D Gaussian Splatting            | Fast, high quality, no dataset needed                          |
| Reconstruction backend   | gsplat                           | MPS support for M2; cleaner than Nerfstudio for production use |
| Mesh extraction          | SuGaR (on demand)                | Produces editable mesh from 3DGS without pretraining           |
| SfM approach             | Online SfM via pycolmap          | Real-time pose estimation during capture                       |
| Compute location         | MacBook (local server)           | Avoids cloud GPU costs; good fit for M2 hardware               |
| Data transport           | WebRTC via aiortc                | Reliable, low latency on local network                         |
| Mobile framework         | React Native (TypeScript)        | JS ecosystem, viable ARCore integration via native module      |
| Server language          | Python                           | Shared ecosystem with gsplat, pycolmap, SuGaR, torch           |
| Scene viewing            | WebGL viewer served from MacBook | No native Android 3D rendering required                        |
| Scene persistence        | Local filesystem on MacBook      | Simple; no database overhead at this stage                     |

---

## 10. Open Problems

The following are known hard problems deferred to later stages:

**Mobile 3D rendering in React Native.** Rendering a 3DGS scene natively inside a React Native app requires either a custom Metal / OpenGL ES native module exposed via JSI, a Three.js based Gaussian renderer inside a WebView, or a Unity / Filament view embedded in React Native. The WebGL viewer served from MacBook sidesteps this for now.

**Confidence and coverage visualization.** Showing the user a color-coded map of which areas are well-reconstructed is the key feedback loop feature. This maps to active reconstruction research (BayesNeRF, Active NeRF, next-best-view planning) and is not yet a solved, shippable feature.

**Scene file size.** A `.ply` file for a room can be tens to hundreds of MB. Compression before serving and resumable transfers will be needed as scene complexity grows.

**Mesh quality at room scale.** SuGaR mesh output is imperfect for complex surfaces and reflective materials. A hybrid simplified room model approach may prove more practical for interior design workflows than a fully extracted mesh.

---

## 11. Out of Scope (Current Phase)

- Cloud infrastructure or remote reconstruction
- iOS support
- Cross-platform desktop support
- STUN / TURN servers
- Multi-user or collaborative capture
- Business model or monetization
