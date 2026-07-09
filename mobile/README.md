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
- **React Navigation** (native-stack) — screen navigation
- **Async Storage** — local data persistence
- **react-native-safe-area-context** — safe-area layout for navigation
- **Local mDNS Expo module** (`modules/mdns`, Android `NsdManager`) — discovers
  the MacBook server on the local network

## TypeScript

The project uses TypeScript for type safety. Source files are in `./src/`:

- `src/App.tsx` — main app component
- `src/screens/` — screen components
- `src/services/` — business logic

Local native modules live in `./modules/` (e.g. `modules/mdns`).

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
- [React Navigation](https://reactnavigation.org/)
- [React Native](https://reactnative.dev/)
