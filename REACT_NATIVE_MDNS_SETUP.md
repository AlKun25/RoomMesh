# React Native mDNS Implementation Setup Guide

This guide covers the complete setup for mDNS service discovery in the React Native mobile app.

## Project Structure

```
mobile/
├── src/
│   ├── services/
│   │   ├── MdnsDiscovery.ts          # mDNS discovery service
│   │   └── ServerPreferences.ts      # AsyncStorage preferences
│   ├── screens/
│   │   └── ServerSettingsScreen.tsx  # Settings UI component
│   └── ... (other app files)
├── android/
│   └── app/src/main/java/
│       └── com/roommesh/modules/
│           └── MdnsModule.kt         # React Native bridge to Android mDNS
└── package.json                      # Dependencies
```

## Installation Steps

### 1. Install Dependencies

```bash
cd mobile
npm install
# or
yarn install
```

Key dependencies:
- `@react-native-async-storage/async-storage` — Persistent settings storage
- `react-native` — Core framework
- `@react-navigation/*` — Navigation

### 2. Android Setup

#### Copy Kotlin Module

1. Copy `android/app/src/main/java/com/roommesh/modules/MdnsModule.kt` to your Android project's `android/app/src/main/java/com/roommesh/modules/` directory

2. Create `MdnsPackage.kt` in the same directory:

```kotlin
import com.facebook.react.ReactPackage
import com.facebook.react.bridge.NativeModule
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.uimanager.ViewManager
import com.roommesh.modules.MdnsModule

class MdnsPackage : ReactPackage {
    override fun createNativeModules(reactContext: ReactApplicationContext): List<NativeModule> {
        return listOf(MdnsModule(reactContext))
    }

    override fun createViewManagers(reactContext: ReactApplicationContext): List<ViewManager<*, *>> {
        return emptyList()
    }
}
```

#### Register Package

In your `MainApplication.kt`:

```kotlin
import com.roommesh.modules.MdnsPackage

class MainApplication : Application(), ReactApplication {
    private val mReactNativeHost = object : ReactNativeHost(this) {
        override fun getPackages(): List<ReactPackage> {
            return listOf(
                MainReactPackage(),
                MdnsPackage(),  // Add this
                // ... other packages
            )
        }
        // ... rest of implementation
    }
    // ...
}
```

#### Update build.gradle

Add to `android/app/build.gradle` dependencies:

```gradle
dependencies {
    // ... existing dependencies
    implementation 'com.facebook.react:react-native:+'
}
```

### 3. Integrate TypeScript Services

Copy the following files to your React Native project:

- `src/services/MdnsDiscovery.ts` → `mobile/src/services/`
- `src/services/ServerPreferences.ts` → `mobile/src/services/`
- `src/screens/ServerSettingsScreen.tsx` → `mobile/src/screens/`

### 4. Add Settings Screen to Navigation

In your main navigation file (e.g., `src/navigation/RootNavigator.tsx`):

```typescript
import { ServerSettingsScreen } from '../screens/ServerSettingsScreen';

export const RootNavigator = () => {
  return (
    <NavigationContainer>
      <Stack.Navigator>
        {/* ... other screens */}
        <Stack.Screen
          name="ServerSettings"
          component={ServerSettingsScreen}
          options={{ title: 'Server Settings' }}
        />
      </Stack.Navigator>
    </NavigationContainer>
  );
};
```

### 5. Initialize Server Connection on App Start

In your app initialization (e.g., `App.tsx`):

```typescript
import { useEffect } from 'react';
import MdnsDiscovery from './src/services/MdnsDiscovery';
import { serverPreferences } from './src/services/ServerPreferences';

export default function App() {
  useEffect(() => {
    const initializeServerConnection = async () => {
      try {
        const config = await MdnsDiscovery.getServerConfig(serverPreferences);
        console.log(`Connected to: ${config.host}:${config.port}`);
        // Store config for use throughout app
        // e.g., in Redux, Context, or local state
      } catch (error) {
        console.error('Failed to initialize server connection:', error);
        // User will need to configure manually via Settings
      }
    };

    initializeServerConnection();

    return () => {
      MdnsDiscovery.cleanup();
    };
  }, []);

  return (
    <RootNavigator />
  );
}
```

### 6. Use Server Config in Signaling

When initializing WebRTC or API calls, use the stored server configuration:

```typescript
import { serverPreferences } from './src/services/ServerPreferences';

const initializeWebRTC = async () => {
  const host = await serverPreferences.getServerHost();
  const port = await serverPreferences.getServerPort();

  const signalingUrl = `http://${host}:${port}/signal`;
  // Initialize WebRTC with signalingUrl
};
```

## Feature Overview

### ServerSettingsScreen Component

The React Native settings screen provides:

- **Auto-discovery toggle**: Enable/disable mDNS discovery
- **Discover button**: Automatically finds and connects to MacBook
- **Manual server configuration**: Host and port input fields
- **Test connection**: Verify connectivity before saving
- **Connection status**: Visual indicator of connection state
- **Settings persistence**: All settings saved with AsyncStorage

### MdnsDiscovery Service

Public methods:

```typescript
// Discover a service on the network
async discoverService(
  serviceName: string = 'macbook',
  timeout: number = 5000
): Promise<DiscoveryResult | null>

// Get server configuration with fallback
async getServerConfig(preferences: ServerPreferences): Promise<ServerConfig>

// Clean up resources
cleanup(): void
```

### ServerPreferences Service

Methods for managing server settings:

```typescript
// Read settings
await serverPreferences.getMdnsEnabled(): Promise<boolean>
await serverPreferences.getServerHost(): Promise<string>
await serverPreferences.getServerPort(): Promise<number>
await serverPreferences.getLastResolvedHost(): Promise<string | null>

// Write settings
await serverPreferences.setMdnsEnabled(enabled: boolean): Promise<void>
await serverPreferences.setServerHost(host: string): Promise<void>
await serverPreferences.setServerPort(port: number): Promise<void>
await serverPreferences.setLastResolvedHost(host: string): Promise<void>

// Clear all settings
await serverPreferences.clearAll(): Promise<void>
```

## Testing

### Manual Testing Steps

1. **Build and deploy**:
   ```bash
   npm run build:android
   # or
   npm run android
   ```

2. **Verify setup**:
   - Open app on Pixel 7
   - Navigate to Settings
   - Verify mDNS is enabled by default

3. **Test auto-discovery**:
   - Ensure MacBook is running and connected to same WiFi
   - Tap "Discover Server"
   - Verify server host and port are populated
   - Tap "Test Connection" — should show "Connected"

4. **Test manual configuration**:
   - Disable mDNS toggle
   - Manually enter MacBook IP and port (e.g., 192.168.1.100:8000)
   - Save settings
   - Tap "Test Connection"

5. **Test persistence**:
   - Close and reopen app
   - Verify saved settings are restored

### Android Emulator Testing

If testing on emulator:
- Emulator has limited mDNS support
- Manual IP entry is recommended
- Use your host machine's IP: `10.0.2.2` (special alias in Android emulator)

## Troubleshooting

### mDNS Discovery Not Finding Service

**Issue**: "Discover Server" returns no results

**Solutions**:
1. Verify both devices are on same WiFi network
2. Verify MacBook server is running: `uv run python -m src.main`
3. Verify mDNS is advertised: `dns-sd -B _http._tcp` (macOS)
4. Check firewall settings
5. Use manual IP entry as fallback

### Connection Test Fails

**Issue**: "Test Connection" shows error

**Solutions**:
1. Verify host/port is correct
2. Verify MacBook server is still running
3. Check network connectivity between devices
4. Try pinging the server: `ping <host>`
5. Check if port 8000 is open: `nc -zv <host> 8000`

### App Crashes on Startup

**Issue**: App crashes when trying to initialize mDNS

**Solutions**:
1. Ensure MdnsPackage is registered in MainApplication
2. Verify AsyncStorage is properly installed
3. Check Logcat for error messages: `adb logcat | grep MdnsModule`
4. Try clearing app data: `adb shell pm clear com.roommesh`

### Settings Not Persisting

**Issue**: Settings are cleared after app restart

**Solutions**:
1. Verify AsyncStorage is installed: `npm list @react-native-async-storage/async-storage`
2. Check that directory permissions are correct
3. Test AsyncStorage directly:
   ```typescript
   import AsyncStorage from '@react-native-async-storage/async-storage';
   await AsyncStorage.setItem('test', 'value');
   const value = await AsyncStorage.getItem('test');
   console.log(value); // Should be 'value'
   ```

## Architecture Notes

- **TypeScript**: Fully typed for compile-time safety
- **React Native**: Cross-platform compatible (Android + iOS ready)
- **AsyncStorage**: Reliable, device-specific storage
- **Native Bridge**: Kotlin module bridges React Native to Android APIs
- **Error Handling**: Graceful fallbacks at each step
- **Timeout Protection**: Auto-cleanup after discovery timeout

## Next Steps

1. Integrate with WebRTC signaling module
2. Add scene loading with resolved server address
3. Implement network state detection for auto-reconnect
4. Add server health monitoring
5. Support iOS with similar native module (objective-c)
