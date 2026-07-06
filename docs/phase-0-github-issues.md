# Phase 0: Foundations — GitHub Issues

Copy each section below into a new GitHub issue. Title is the first line, everything after is the issue body.

---

## Issue 1: Set up MacBook FastAPI project skeleton with uvicorn

**Description**
Create the base FastAPI project on the MacBook that later phases will build on, including a health check endpoint.

**Tasks**
- Create the project structure with separate areas for signaling, scene serving, and shared config
- Add a `GET /health` endpoint returning basic server status
- Add environment or config handling for values reused later, such as the scans directory path

**Acceptance criteria**
- `uvicorn` runs the app locally without errors
- `GET /health` returns a 200 response with a status payload

---

## Issue 2: Configure mDNS so the MacBook is reachable at macbook.local

**Description**
Make sure the MacBook is discoverable on the local network at `macbook.local` from an Android client.

**Tasks**
- Confirm Bonjour advertises the MacBook as `macbook.local` by default
- Test whether the Pixel 7 resolves `macbook.local` out of the box, since Android does not always resolve mDNS automatically
- If needed, integrate `NsdManager` or a small mDNS resolution library on the Android side
- Add a fallback config option for manual IP entry in case mDNS proves unreliable on a given network

**Acceptance criteria**
- The Pixel 7 can resolve and reach `macbook.local` on the same local network
- A manual IP fallback exists and works if mDNS resolution fails

---

## Issue 3: Set up React Native and TypeScript project skeleton for the mobile client

**Description**
Scaffold the mobile client project using bare React Native, since later native modules for ARCore and camera control require native code access.

**Tasks**
- Initialize a bare React Native project with TypeScript (not the Expo managed workflow)
- Set up the base folder structure and navigation shell
- Confirm the app builds and runs on the Pixel 7

**Acceptance criteria**
- The app builds and launches on the Pixel 7
- Project structure supports adding native modules in Phase 1

---

## Issue 4: Integrate aiortc and react-native-webrtc for a minimal peer connection

**Description**
Establish a minimal WebRTC peer connection between the MacBook server and the mobile client.

**Tasks**
- Add `aiortc` to the MacBook server
- Add `react-native-webrtc` to the mobile client
- Confirm version compatibility between the two, particularly around codec negotiation
- Build the connection without audio tracks, since only data or video is needed

**Acceptance criteria**
- A peer connection can be established between phone and MacBook on the local network
- No audio track is present in the connection

---

## Issue 5: Implement SDP offer and answer exchange over macbook.local:8000/signal

**Description**
Implement the signaling exchange needed to establish the WebRTC connection.

**Tasks**
- Decide whether signaling uses plain HTTP request and response, or a websocket if renegotiation will be needed later (relevant for reconnect handling in Phase 7)
- Implement the SDP offer and answer exchange over `macbook.local:8000/signal`
- Implement ICE candidate gathering and exchange, even without STUN or TURN servers

**Acceptance criteria**
- Phone and MacBook complete an SDP offer and answer exchange successfully
- ICE candidates are exchanged and a connection is established without STUN or TURN

---

## Issue 6: Verify a DataChannel or MediaChannel opens and can carry a test payload

**Description**
Confirm the underlying channel used for frame transport works before any real frame data is sent.

**Tasks**
- Decide whether frames will travel over a DataChannel for more control, or a MediaChannel using a native video track for simpler codec handling
- Send a small JSON payload or a single test image from phone to MacBook
- Confirm the payload arrives with byte for byte integrity

**Acceptance criteria**
- A DataChannel or MediaChannel opens successfully between phone and MacBook
- A test payload sent from the phone is received intact on the MacBook

---

## Issue 7: Test signaling and connection flow on real network conditions

**Description**
Validate that the signaling and WebRTC connection flow set up in Phase 0 actually holds up outside of an ideal development setup, since mDNS resolution and local WebRTC connectivity are both sensitive to real world network conditions.

**Tasks**
- Test the full connection flow with both devices on the same home Wi-Fi network
- Test what happens if the phone accidentally falls back to cellular data instead of Wi-Fi
- Test against a router with multicast restrictions or AP isolation enabled, since these can silently break mDNS
- Document any failure modes found and whether the manual IP fallback from Issue 2 resolves them

**Acceptance criteria**
- The connection flow is confirmed working on at least one real home network, not just localhost or a controlled test environment
- Known failure modes (cellular fallback, AP isolation, multicast blocking) are documented along with whether the fallback path handles them
