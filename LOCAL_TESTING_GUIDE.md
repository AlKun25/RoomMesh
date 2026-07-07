# Local Testing Guide: mDNS Discovery

This guide walks you through running the complete mDNS implementation locally on a MacBook and Android device (Pixel 7).

## Prerequisites

### Hardware
- MacBook (M1/M2/M3 or Intel) running macOS
- Android device (Pixel 7 or compatible)
- USB cable for Android device
- Both devices on the same WiFi network

### Software Setup
- Python 3.13+ installed on MacBook
- Node.js 18+ and bun installed
- Android Studio with SDK tools
- Git

### Network Requirements
- MacBook and Pixel 7 on same WiFi network
- WiFi network supports mDNS (most home/office networks do)
- No network isolation between devices (check firewall/router settings)

## Part 1: Start MacBook Server

### 1.1 Clone and Setup Repository

```bash
# Clone the repository
git clone https://github.com/AlKun25/RoomMesh.git
cd RoomMesh

# Ensure you're on the issue-2 branch
git checkout issue-2

# Install Python dependencies
uv sync
```

### 1.2 Start the Server

```bash
# Start the server with mDNS enabled (default)
uv run python -m src.main

# You should see output like:
# INFO:     Uvicorn running on http://127.0.0.1:8000
# INFO:     Registered mDNS service: macbook.local on 192.168.X.X:8000
```

**Note**: The server will bind to `127.0.0.1` but advertise itself on mDNS with your actual local IP.

### 1.3 Verify mDNS Service is Running (macOS)

In a separate terminal on the MacBook:

```bash
# Browse for HTTP services on the network
dns-sd -B _http._tcp

# You should see output like:
# DATE TIME  ...   macbook._http._tcp.         local.

# Look up the specific service
dns-sd -L macbook _http._tcp

# Should show:
# macbook._http._tcp.local. 
#   hostname = MacBook-Pro.local.
#   address = 192.168.X.X
#   port = 8000

# Test DNS resolution
ping macbook.local

# Should resolve to your local IP
```

**Troubleshooting mDNS on MacBook:**
- If `dns-sd -B` doesn't show the service:
  - Check the server is running: `lsof -i :8000`
  - Check server logs for errors
  - Restart the server
  - Restart Bonjour: `sudo launchctl stop com.apple.mDNSResponder && sudo launchctl start com.apple.mDNSResponder`

## Part 2: Build and Deploy React Native App

### 2.1 Setup React Native Project

```bash
# Navigate to mobile directory
cd mobile

# Install dependencies with bun
bun install

# Verify Android SDK is installed
echo $ANDROID_HOME  # Should print SDK path, if not:
# Add to ~/.zshrc or ~/.bash_profile:
# export ANDROID_HOME=$HOME/Library/Android/sdk
# export PATH=$PATH:$ANDROID_HOME/emulator:$ANDROID_HOME/platform-tools
```

### 2.2 Connect Android Device via USB

```bash
# Plug in your Pixel 7 via USB

# Enable Developer Options on Pixel 7:
# 1. Go to Settings > About phone
# 2. Tap "Build number" 7 times
# 3. Go back, enter Developer options
# 4. Enable "USB debugging"

# Verify device is connected
adb devices

# You should see:
# List of attached devices
# XXXXXXXXXXXXXXXX   device
```

### 2.3 Build and Deploy App

```bash
# From the mobile directory
# Build and deploy to connected device
npm run android
# or
yarn android
# or
bun run android

# This will:
# 1. Build the React Native APK
# 2. Install it on the device
# 3. Launch the app

# First build takes 5-10 minutes, subsequent builds are faster
```

### 2.4 Verify App is Running

```bash
# Watch app logs in real-time
adb logcat | grep -E "RoomMesh|MdnsModule"

# You should see the app starting up
```

## Part 3: Test mDNS Discovery

### 3.1 Access Settings Screen

1. **On the Pixel 7:**
   - Open the RoomMesh app
   - Navigate to Settings (or Settings screen if it's the home screen)
   - You should see "Server Settings" screen with:
     - "Auto-discover server (mDNS)" toggle (enabled by default)
     - "Discover Server" button
     - Manual Host and Port input fields
     - "Test Connection" button

### 3.2 Test Auto-Discovery

1. **Ensure both devices are on same WiFi:**
   ```bash
   # On MacBook, check your network
   ifconfig | grep -A 5 "en0"  # en0 is usually WiFi
   
   # On Pixel 7, go to: Settings > Network & internet > WiFi > View details
   ```

2. **Tap "Discover Server" button:**
   - Button shows loading spinner
   - After 3-5 seconds, you should see:
     - "Discovered: 192.168.X.X:8000" message
     - Server Host field populated with IP
     - Server Port field shows 8000

3. **If discovery fails:**
   - Check logs: `adb logcat | grep MdnsModule`
   - Try manual entry (see section 3.3)

### 3.3 Test Manual Configuration (Fallback)

1. **Toggle off "Auto-discover server"** if mDNS failed

2. **Manually enter server details:**
   - Host: `192.168.X.X` (your MacBook's IP)
   - Port: `8000`
   
   Or try using the hostname:
   - Host: `macbook.local`
   - Port: `8000`

3. **Tap "Test Connection":**
   - Button shows loading state
   - After 1-2 seconds:
     - Success (green dot): ✓ Connection successful
     - Error (red dot): ✗ Check IP/port and try again

4. **Tap "Save Settings":**
   - Settings are persisted locally

### 3.4 Verify Connection

Check server logs on MacBook for incoming requests:

```bash
# In terminal where server is running, you should see:
# GET /health HTTP/1.1" 200 OK
# when app tests the connection
```

## Part 4: Test Persistence and Restart

### 4.1 Verify Settings Persist

1. **Note the saved host and port**
2. **Close the app completely**
3. **Reopen the app**
4. **Navigate back to Settings**
5. **Confirm host and port are still there**

### 4.2 Test Auto-Connect on App Start

1. **Modify `App.tsx` to log the server config:**
   ```typescript
   useEffect(() => {
     const initializeServerConnection = async () => {
       try {
         const config = await MdnsDiscovery.getServerConfig(serverPreferences);
         console.log(`Connected to: ${config.host}:${config.port}`);
       } catch (error) {
         console.error('Failed to initialize:', error);
       }
     };
     initializeServerConnection();
   }, []);
   ```

2. **Restart app and check logs:**
   ```bash
   adb logcat | grep "Connected to"
   ```

## Part 5: Comprehensive Testing Scenarios

### Scenario 1: Fresh Install
```
Expected:
1. App installs successfully
2. Settings screen opens
3. mDNS discovery enabled by default
4. "Discover Server" button is tappable
5. Tap discover → finds MacBook
6. Connection test succeeds
7. Settings saved on app restart
```

### Scenario 2: Network Change
```
Setup: Connected to WiFi A, discovered MacBook
Test: 
1. Switch Pixel 7 to WiFi B (without MacBook)
2. Open Settings
3. Connection test should fail
4. Switch back to WiFi A
5. Tap discover again → should find MacBook
```

### Scenario 3: Server Restart
```
Setup: Connected to MacBook server
Test:
1. Stop MacBook server (Ctrl+C)
2. On Pixel 7, tap "Test Connection" → should fail
3. Restart MacBook server
4. Wait 2-3 seconds (for mDNS to re-advertise)
5. Tap "Test Connection" → should succeed
```

### Scenario 4: Manual Configuration
```
Setup: mDNS discovery failed
Test:
1. Toggle off "Auto-discover server"
2. Manually enter: 192.168.X.X and 8000
3. Tap "Test Connection" → should succeed
4. Save settings
5. Close and reopen app
6. Settings should persist
```

### Scenario 5: mDNS with Hostname
```
Setup: mDNS enabled
Test:
1. Tap "Discover Server"
2. After success, manually change Host to "macbook.local"
3. Save settings
4. Close and reopen app
5. Tap "Test Connection" → should succeed
```

## Part 6: Debugging Common Issues

### Issue: App Crashes on Startup

**Symptoms**: App crashes immediately when opened

**Solutions**:
```bash
# 1. Check logcat for errors
adb logcat | grep -E "ERROR|EXCEPTION" | tail -20

# 2. Clear app data
adb shell pm clear com.roommesh

# 3. Rebuild
cd mobile && bun run android

# 4. Check that AsyncStorage dependency is installed
npm list @react-native-async-storage/async-storage
```

### Issue: Discover Button Does Nothing

**Symptoms**: Tapping "Discover Server" shows loading but never completes

**Solutions**:
```bash
# 1. Check device logs
adb logcat | grep MdnsModule

# 2. Verify both devices on same network
# On MacBook:
ifconfig | grep -A 5 en0

# On Pixel 7:
Settings > Network & internet > WiFi > View details

# 3. Check if MacBook server is running
lsof -i :8000  # Should show python process

# 4. Verify mDNS is advertised
dns-sd -B _http._tcp  # Should show macbook service

# 5. Try pinging from Pixel 7:
# (requires Android terminal emulator or USB debugging with ping)
adb shell ping macbook.local
```

### Issue: Connection Test Fails

**Symptoms**: Test button shows error (red dot)

**Solutions**:
```bash
# 1. Verify server is running
curl -v http://192.168.X.X:8000/health

# 2. Check firewall allows port 8000
sudo lsof -i :8000

# 3. Verify correct IP address
# On MacBook:
ifconfig | grep "inet " | grep -v 127.0.0.1

# 4. Try connecting via hostname
adb shell ping macbook.local

# 5. Check server logs for connection attempts
# Server should show: GET /health HTTP/1.1" 200 OK
```

### Issue: Settings Don't Persist

**Symptoms**: Settings are cleared after app restart

**Solutions**:
```bash
# 1. Verify AsyncStorage is working
# Create a test in the app console

# 2. Check app has storage permissions
adb shell pm grant com.roommesh android.permission.READ_EXTERNAL_STORAGE
adb shell pm grant com.roommesh android.permission.WRITE_EXTERNAL_STORAGE

# 3. Check device storage is not full
adb shell df

# 4. Clear app cache and try again
adb shell pm clear com.roommesh
```

### Issue: Multiple Servers on Network

**Symptoms**: Discovery finds wrong server

**Solutions**:
1. Verify the service name matches: should be "macbook"
2. Check for other HTTP services: `dns-sd -B _http._tcp`
3. Manually specify IP instead of relying on discovery
4. Consider using a more unique service name if needed

## Part 7: Performance Metrics

### Expected Timings
- App startup: 2-3 seconds
- mDNS discovery: 3-5 seconds
- Connection test: 1-2 seconds
- Settings persistence: < 100ms

### Logs to Monitor

**MacBook Server**:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Registered mDNS service: macbook.local on 192.168.X.X:8000
GET /health HTTP/1.1" 200 OK
```

**Android Device**:
```
D/MdnsModule: Discovery started for: _http._tcp.
D/MdnsModule: Service found: macbook._http._tcp.local.
D/MdnsModule: Service resolved: macbook._http._tcp.local.
I/RoomMesh: Connected to: 192.168.X.X:8000
```

## Part 8: Clean Up

### Reset to Clean State

```bash
# On Pixel 7
adb shell pm clear com.roommesh

# On MacBook (if needed)
rm -rf scans/  # Removes any test scan data

# Stop server
Ctrl+C in server terminal
```

### Disable mDNS (Testing Manual Only)

```bash
# Set environment variable
export MDNS_ENABLED=false

# Start server
uv run python -m src.main

# mDNS service will not be advertised
# Only manual configuration will work on app
```

## Part 9: Next Steps

Once local testing is successful:

1. **Test WebRTC Connection**
   - Integrate with WebRTC signaling using discovered server address
   - Test frame streaming from Pixel 7 to MacBook

2. **Test Scene Retrieval**
   - Capture a test scene
   - Retrieve scene data via discovered MacBook address

3. **Test Different Networks**
   - Test on home WiFi
   - Test on office WiFi
   - Test on mobile hotspot (if mDNS supported)

4. **Performance Optimization**
   - Monitor discovery timeout durations
   - Optimize connection retry logic
   - Add offline mode with manual configuration

## Quick Reference

### Common Commands

```bash
# MacBook - Start server
cd RoomMesh && uv run python -m src.main

# MacBook - Verify mDNS
dns-sd -L macbook _http._tcp
ping macbook.local

# Android - Connect device
adb devices

# Android - Deploy app
cd mobile && npm run android

# Android - View logs
adb logcat | grep -E "RoomMesh|MdnsModule"

# Android - Test ping (if shell available)
adb shell ping 192.168.X.X

# Android - Clear app data
adb shell pm clear com.roommesh
```

### URLs for Manual Testing

```
MacBook server: http://127.0.0.1:8000
Health check: http://192.168.X.X:8000/health
API docs: http://192.168.X.X:8000/docs
```

### Settings Defaults

```
mDNS Enabled: true
Server Host: (empty, fill via discovery or manual)
Server Port: 8000
Service Name: macbook
```

---

**Support**: If you encounter issues not covered here, check:
1. Server logs on MacBook
2. `adb logcat | grep MdnsModule` on Android
3. Network connectivity between devices
4. Firewall/router settings allowing mDNS
