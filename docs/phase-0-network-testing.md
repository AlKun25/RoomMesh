# Phase 0 — Real-Network Testing Runbook (Issue #7)

Validate that the signaling + WebRTC connection flow, plus the new camera-video
capture path, holds up on a real home network rather than just loopback. mDNS
resolution and LAN WebRTC connectivity are both sensitive to real-world router
behaviour (AP isolation, multicast filtering) and to the phone silently falling
back to cellular.

This is a **manual** procedure — it requires a physical Pixel 7, the MacBook, and
a real router whose settings you can change. Run it, then fill in the
[Results](#results) table.

## What the app now reports

The client distinguishes failure modes instead of collapsing them into a single
"Failed" (see `mobile/src/services/WebRTCService.ts`). The status line on the
**Server Settings** and **Capture** screens shows one of:

| Reported status                         | Meaning                                                                                                           |
| --------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `Failed — server unreachable (ws)`      | The `/signal` WebSocket never opened. Wrong host, phone on a different network/cellular, or a firewall.           |
| `Failed — peer connection failed (ice)` | Signaling succeeded but the peers never connected. AP isolation or UDP/multicast blocked between the two devices. |
| `Failed — signaling error`              | A malformed/unexpected signaling message.                                                                         |
| `Discovery Failed` (alert on Discover)  | mDNS (`macbook.local`) did not resolve — treat as **mdns-timeout**.                                               |
| `Connected` / `Streaming to MacBook`    | Success.                                                                                                          |

The **manual IP fallback** is the Server Host / Server Port fields on the Server
Settings screen (persisted via `ServerPreferences`). "Does fallback resolve it?"
below means: with mDNS off and the MacBook's LAN IP typed in manually, does the
flow succeed?

## Preconditions

1. **Start the server** on the MacBook:

   ```bash
   uv run uvicorn src.main:app --host 0.0.0.0 --port 8000
   ```

   Confirm the mDNS log line `Registering mDNS service: macbook.local ...` and
   note the MacBook's LAN IP (`ipconfig getifaddr en0`).
2. **Install the app** on the Pixel 7 as a dev-client build (the CAMERA
   permission is a native change):

   ```bash
   cd mobile && npm run prebuild && npm run android
   ```

3. Grant the camera permission when prompted.

## Procedure (per scenario)

For each scenario in the matrix:

1. Put the network into the scenario's state (see the row).
2. On **Server Settings**: toggle mDNS as noted, tap **Discover Server**
   (mDNS rows) or type the MacBook IP (manual rows), then **Test Connection**
   (HTTP `/health`) and **Connect (WebRTC)**.
3. Open **Camera Capture** → **Start Camera** (confirm preview) →
   **Connect & Stream**.
4. On success, confirm frames are being written on the MacBook:

   ```bash
   ls scans/*/frames | tail        # JPEGs accumulating
   cat scans/*/metadata.json       # frame_count > 0
   ```

5. Record the reported status and whether the manual-IP fallback recovers the
   scenario.

## Scenario matrix (expected)

| #   | Scenario                                 | How to set it up                                                           | Expected reported status                                       | Manual-IP fallback resolves?                               |
| --- | ---------------------------------------- | -------------------------------------------------------------------------- | -------------------------------------------------------------- | ---------------------------------------------------------- |
| 1   | Same home Wi-Fi (happy path)             | Both devices on the same 2.4/5 GHz SSID                                    | `Connected` / `Streaming to MacBook`                           | n/a (already works)                                        |
| 2   | Phone on cellular / different subnet     | Disable Wi-Fi on the phone (or join a guest SSID on another subnet)        | `Failed — server unreachable (ws)`                             | **No** — MacBook not routable from cellular / other subnet |
| 3   | Router AP isolation ("client isolation") | Enable AP/client isolation in the router admin, both on the same SSID      | mDNS may resolve, then `Failed — peer connection failed (ice)` | **No** — isolation blocks device-to-device UDP             |
| 4   | Multicast filtered / mDNS blocked        | Enable "block multicast" / disable mDNS/Bonjour reflection in router admin | Discover → `Discovery Failed` (mdns-timeout)                   | **Yes** — typing the LAN IP bypasses mDNS                  |

The "expected" column is the hypothesis; the point of the run is to confirm or
correct it and capture the actuals below.

## Results

Fill in after running. Home network: `__________` Router model: `__________`
Date: `__________`

| #   | Scenario                 | Reported status (actual) | mDNS resolved? | WebRTC connected? | Frames stored? | Manual-IP fallback worked? | Notes |
| --- | ------------------------ | ------------------------ | -------------- | ----------------- | -------------- | -------------------------- | ----- |
| 1   | Same home Wi-Fi          |                          |                |                   |                |                            |       |
| 2   | Cellular / other subnet  |                          |                |                   |                |                            |       |
| 3   | AP isolation             |                          |                |                   |                |                            |       |
| 4   | Multicast / mDNS blocked |                          |                |                   |                |                            |       |

### Interpretation guide

| Diagnostic reason | Likely cause                                             | Does the manual-IP fallback help?                          |
| ----------------- | -------------------------------------------------------- | ---------------------------------------------------------- |
| `mdns-timeout`    | Router drops multicast / no mDNS reflection across bands | **Yes** — manual IP skips discovery entirely               |
| `ws-unreachable`  | MacBook not routable: cellular, other subnet, firewall   | **Only** if a route to the MacBook exists (same L2/subnet) |
| `ice-failed`      | AP isolation / UDP blocked between the two devices       | **No** — fallback fixes addressing, not reachability       |
| `signaling-error` | Protocol bug / version skew                              | No — investigate the signaling code                        |

## Acceptance criteria (Issue #7)

- [ ] The flow is confirmed working (connected + frames stored) on at least one
      real home network — scenario 1.
- [ ] The known failure modes (cellular fallback, AP isolation, multicast
      blocking) are exercised and documented above, each with whether the manual
      IP fallback resolves it.
