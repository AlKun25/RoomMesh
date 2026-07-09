# RoomMesh Mobile (Expo)

React Native mobile app for room scanning and 3D reconstruction using Expo.

## Prerequisites

- Node.js 18+ (or equivalent)
- Bun (https://bun.sh)
- Physical Android device (API 23+) or Android emulator
- Expo Go app installed on device (optional, for QR code deployment)

## Setup

```bash
cd mobile
bun install
```

## Development

### Start Dev Server
```bash
# Start Metro bundler and show QR code
bun start

# Or with specific platform
bun run dev:android
bun run dev:ios
```

### Scan QR Code (Easiest)
1. Run `bun start`
2. Open Expo Go app on your device
3. Scan the QR code from terminal

### Or Run on Emulator
1. Start Android emulator
2. Run `bun run dev:android`

## Building

### For Local Development
```bash
bun run dev
```

### For Production (EAS Build)
```bash
bun run build
```

## Architecture

The app uses:
- **React Navigation** — screen navigation
- **Async Storage** — local data persistence
- **React Native Gesture Handler** — touch interactions
- **React Native Reanimated** — performant animations
- **Camera Roll** — device media access

## TypeScript

The project uses TypeScript for type safety. Source files are in `../src/`:
- `src/App.tsx` — main app component
- `src/screens/` — screen components
- `src/services/` — business logic

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
- Ensure physical device and dev machine are on same WiFi
- Run `bun start` again and rescan QR code

## Resources

- [Expo Documentation](https://docs.expo.dev/)
- [React Navigation](https://reactnavigation.org/)
- [React Native](https://reactnative.dev/)
