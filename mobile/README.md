# RoomMesh Mobile (Expo)

React Native mobile app for room scanning and 3D reconstruction using Expo.

## Prerequisites

- Node.js 18+ (or equivalent)
- Bun (https://bun.sh)
- Android SDK / platform-tools (for `expo run:android`)
- Physical Android device (API 23+) or Android emulator

## Setup

```bash
cd mobile
bun install
```

## Development

> **Important:** this app ships a **local native module** (`Mdns`, used for mDNS
> server discovery), so it must run as an **Expo dev build** — not Expo Go. Expo
> Go cannot load local native modules, so mDNS (and future ARCore/camera native
> code) will not work under it. Use Expo Go only for UI-only iteration.

### Run a dev build on a device (required for the full app)

```bash
# Generate the native android/ project from app.json (one-time / after native changes)
bun run prebuild

# Build, install, and launch on a connected Pixel 7 (or emulator)
bun run android
```

### Metro dev server (JS reloads)

```bash
# Start the Metro bundler; a running dev build connects to it automatically
bun start
```

## Architecture

The app uses:

- **Expo SDK 51** (RN 0.74.5) with **prebuild / CNG** — native `android/` is
  generated, not committed
- **Expo Router** — file-based navigation from the `app/` directory (typed routes
  enabled); built on React Navigation's native-stack under the hood
- **Async Storage** — local data persistence
- **react-native-safe-area-context** — safe-area layout for navigation
- **Local mDNS Expo module** (`modules/mdns`, Android `NsdManager`) — discovers
  the MacBook server on the local network

## Project layout

The app entry is `expo-router/entry` (set via `main` in `package.json`); routes
are derived from the `app/` directory. Route files are thin layers that re-export
screen implementations kept in `src/`, keeping routing separate from feature logic.

- `app/_layout.tsx` — root navigator (`Stack`)
- `app/index.tsx` — index route; re-exports `ServerSettingsScreen`
- `src/screens/` — screen implementations
- `src/services/` — business logic (mDNS discovery, preferences)
- `modules/` — local native Expo modules (e.g. `modules/mdns`)

To add a screen, create a new file under `app/` (e.g. `app/capture.tsx` →
`/capture`, `app/viewer/[scene].tsx` → `/viewer/:scene`).

## Troubleshooting

### Metro Bundler Stuck

```bash
bun start --reset-cache
```

### Clear All Cache

```bash
rm -rf node_modules .expo
bun install
```

### Device Not Showing

- Ensure the device is connected via USB with debugging enabled (`adb devices`)
- Ensure physical device and dev machine are on the same WiFi
- Re-run `bun run android` to reinstall the dev build

### Rebuild After Native Changes

- After editing `app.json` or anything under `modules/`, re-run
  `bun run prebuild` then `bun run android`

## Resources

- [Expo Documentation](https://docs.expo.dev/)
- [Expo Router](https://docs.expo.dev/router/introduction/)
- [React Native](https://reactnative.dev/)
