# Android mDNS Discovery Implementation Guide

## Overview

This guide provides implementation steps for the Android client side of issue #2 (Configure mDNS so the MacBook is reachable at macbook.local).

## Components to Implement

### 1. MdnsDiscovery Service

Create `android/app/src/main/java/com/roommesh/services/MdnsDiscoveryService.kt`:

```kotlin
import android.content.Context
import android.net.nsd.NsdManager
import android.net.nsd.NsdServiceInfo
import android.util.Log
import kotlin.coroutines.resume
import kotlin.coroutines.suspendCancellableCoroutine

class MdnsDiscoveryService(private val context: Context) {
    private val nsdManager = context.getSystemService(Context.NSD_SERVICE) as NsdManager
    private var discoveryListener: NsdManager.DiscoveryListener? = null
    private var resolveListener: NsdManager.ResolveListener? = null

    data class DiscoveryResult(
        val serviceName: String,
        val host: String,
        val port: Int,
    )

    suspend fun discoverService(
        serviceName: String = "macbook",
        timeout: Long = 5000,
    ): DiscoveryResult? = suspendCancellableCoroutine { continuation ->
        discoveryListener = object : NsdManager.DiscoveryListener {
            override fun onServiceFound(serviceInfo: NsdServiceInfo) {
                Log.d(TAG, "Service found: ${serviceInfo.serviceName}")
                if (serviceInfo.serviceName.contains(serviceName)) {
                    resolveService(serviceInfo, continuation)
                }
            }

            override fun onServiceLost(serviceInfo: NsdServiceInfo) {
                Log.d(TAG, "Service lost: ${serviceInfo.serviceName}")
            }

            override fun onDiscoveryStarted(serviceType: String) {
                Log.d(TAG, "Discovery started for: $serviceType")
            }

            override fun onDiscoveryStopped(serviceType: String) {
                Log.d(TAG, "Discovery stopped for: $serviceType")
            }

            override fun onStartDiscoveryFailed(serviceType: String, errorCode: Int) {
                Log.e(TAG, "Discovery failed: $errorCode")
                continuation.resume(null)
            }

            override fun onStopDiscoveryFailed(serviceType: String, errorCode: Int) {
                Log.e(TAG, "Stop discovery failed: $errorCode")
            }
        }

        nsdManager.discoverServices(
            "_http._tcp.",
            NsdManager.PROTOCOL_DNS_SD,
            discoveryListener,
        )

        // Auto-stop after timeout
        continuation.invokeOnCancellation {
            discoveryListener?.let {
                nsdManager.stopServiceDiscovery(it)
            }
        }
    }

    private fun resolveService(
        serviceInfo: NsdServiceInfo,
        continuation: kotlin.coroutines.Continuation<DiscoveryResult?>,
    ) {
        resolveListener = object : NsdManager.ResolveListener {
            override fun onServiceResolved(serviceInfo: NsdServiceInfo) {
                Log.d(TAG, "Service resolved: ${serviceInfo.serviceName}")
                val result = DiscoveryResult(
                    serviceName = serviceInfo.serviceName,
                    host = serviceInfo.host.hostAddress ?: "localhost",
                    port = serviceInfo.port,
                )
                discoveryListener?.let {
                    nsdManager.stopServiceDiscovery(it)
                }
                continuation.resume(result)
            }

            override fun onResolveFailed(serviceInfo: NsdServiceInfo, errorCode: Int) {
                Log.e(TAG, "Resolve failed: $errorCode")
                continuation.resume(null)
            }
        }

        nsdManager.resolveService(serviceInfo, resolveListener)
    }

    fun cleanup() {
        discoveryListener?.let {
            try {
                nsdManager.stopServiceDiscovery(it)
            } catch (e: Exception) {
                Log.w(TAG, "Error stopping discovery", e)
            }
        }
    }

    companion object {
        private const val TAG = "MdnsDiscoveryService"
    }
}
```

### 2. Server Settings Storage

Create `android/app/src/main/java/com/roommesh/preferences/ServerPreferences.kt`:

```kotlin
import android.content.Context
import androidx.datastore.preferences.core.*
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

val Context.serverPreferences by preferencesDataStore(name = "server_preferences")

class ServerPreferences(context: Context) {
    private val dataStore = context.serverPreferences

    companion object {
        val MDNS_ENABLED = booleanPreferencesKey("mdns_enabled")
        val SERVER_HOST = stringPreferencesKey("server_host")
        val SERVER_PORT = intPreferencesKey("server_port")
        val LAST_RESOLVED_HOST = stringPreferencesKey("last_resolved_host")
    }

    val mdnsEnabledFlow: Flow<Boolean> = dataStore.data.map {
        it[MDNS_ENABLED] ?: true
    }

    val serverHostFlow: Flow<String> = dataStore.data.map {
        it[SERVER_HOST] ?: ""
    }

    val serverPortFlow: Flow<Int> = dataStore.data.map {
        it[SERVER_PORT] ?: 8000
    }

    suspend fun setMdnsEnabled(enabled: Boolean) {
        dataStore.edit { it[MDNS_ENABLED] = enabled }
    }

    suspend fun setServerHost(host: String) {
        dataStore.edit { it[SERVER_HOST] = host }
    }

    suspend fun setServerPort(port: Int) {
        dataStore.edit { it[SERVER_PORT] = port }
    }

    suspend fun setLastResolvedHost(host: String) {
        dataStore.edit { it[LAST_RESOLVED_HOST] = host }
    }
}
```

### 3. React Native Bridge (TypeScript)

Create `android/app/src/main/java/com/roommesh/MdnsModule.kt`:

```kotlin
import com.facebook.react.bridge.Promise
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReactContextBaseJavaModule
import com.facebook.react.bridge.ReactMethod
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class MdnsModule(reactContext: ReactApplicationContext) :
    ReactContextBaseJavaModule(reactContext) {

    private val mdnsService = MdnsDiscoveryService(reactContext)
    private val scope = CoroutineScope(Dispatchers.Default)

    override fun getName() = "MdnsModule"

    @ReactMethod
    fun discoverService(serviceName: String, timeout: Int, promise: Promise) {
        scope.launch {
            try {
                val result = mdnsService.discoverService(serviceName, timeout.toLong())
                if (result != null) {
                    promise.resolve(mapOf(
                        "serviceName" to result.serviceName,
                        "host" to result.host,
                        "port" to result.port,
                    ))
                } else {
                    promise.reject("DISCOVERY_FAILED", "Could not discover service")
                }
            } catch (e: Exception) {
                promise.reject("DISCOVERY_ERROR", e.message)
            }
        }
    }

    @ReactMethod
    fun cleanup() {
        mdnsService.cleanup()
    }
}
```

### 4. React Native Integration (TypeScript)

Create `src/services/MdnsDiscovery.ts`:

```typescript
import { NativeModules, Platform } from "react-native";

interface DiscoveryResult {
  serviceName: string;
  host: string;
  port: number;
}

interface ServerConfig {
  host: string;
  port: number;
  useMdns: boolean;
}

class MdnsDiscoveryService {
  private nativeModule =
    Platform.OS === "android" ? NativeModules.MdnsModule : null;

  async discoverService(
    serviceName: string = "macbook",
    timeout: number = 5000,
  ): Promise<DiscoveryResult | null> {
    if (!this.nativeModule) {
      console.warn("mDNS discovery not available on this platform");
      return null;
    }

    try {
      return await this.nativeModule.discoverService(serviceName, timeout);
    } catch (error) {
      console.error("mDNS discovery failed:", error);
      return null;
    }
  }

  async getServerConfig(preferences: ServerPreferences): Promise<ServerConfig> {
    const useMdns = await preferences.getMdnsEnabled();

    if (useMdns) {
      const discovered = await this.discoverService();
      if (discovered) {
        return {
          host: discovered.host,
          port: discovered.port,
          useMdns: true,
        };
      }
    }

    // Fallback to manual configuration
    const host = await preferences.getServerHost();
    const port = await preferences.getServerPort();

    if (!host) {
      throw new Error("No server configured and mDNS discovery failed");
    }

    return {
      host,
      port,
      useMdns: false,
    };
  }

  cleanup() {
    if (this.nativeModule?.cleanup) {
      this.nativeModule.cleanup();
    }
  }
}

export default new MdnsDiscoveryService();
```

### 5. Settings Screen UI

Create `src/screens/ServerSettingsScreen.tsx`:

```typescript
import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Switch,
  ActivityIndicator,
} from 'react-native';
import MdnsDiscovery from '../services/MdnsDiscovery';
import ServerPreferences from '../preferences/ServerPreferences';

export const ServerSettingsScreen: React.FC = () => {
  const [mdnsEnabled, setMdnsEnabled] = useState(true);
  const [serverHost, setServerHost] = useState('');
  const [serverPort, setServerPort] = useState('8000');
  const [discovering, setDiscovering] = useState(false);
  const [discoveredHost, setDiscoveredHost] = useState('');

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    const prefs = new ServerPreferences();
    const mdns = await prefs.getMdnsEnabled();
    const host = await prefs.getServerHost();
    const port = await prefs.getServerPort();

    setMdnsEnabled(mdns);
    setServerHost(host);
    setServerPort(port.toString());
  };

  const handleDiscoverServer = async () => {
    setDiscovering(true);
    try {
      const result = await MdnsDiscovery.discoverService();
      if (result) {
        setDiscoveredHost(`${result.host}:${result.port}`);
        setServerHost(result.host);
        setServerPort(result.port.toString());
      } else {
        setDiscoveredHost('Discovery failed');
      }
    } finally {
      setDiscovering(false);
    }
  };

  const handleSave = async () => {
    const prefs = new ServerPreferences();
    await prefs.setMdnsEnabled(mdnsEnabled);
    await prefs.setServerHost(serverHost);
    await prefs.setServerPort(parseInt(serverPort));
    // Show success message
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Server Settings</Text>

      <View style={styles.section}>
        <Text style={styles.label}>Auto-discover server (mDNS)</Text>
        <Switch
          value={mdnsEnabled}
          onValueChange={setMdnsEnabled}
        />
      </View>

      {mdnsEnabled && (
        <TouchableOpacity
          style={styles.button}
          onPress={handleDiscoverServer}
          disabled={discovering}
        >
          {discovering ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.buttonText}>Discover Server</Text>
          )}
        </TouchableOpacity>
      )}

      {discoveredHost ? (
        <Text style={styles.info}>Discovered: {discoveredHost}</Text>
      ) : null}

      <View style={styles.section}>
        <Text style={styles.label}>Server Host</Text>
        <TextInput
          style={styles.input}
          placeholder="192.168.1.1"
          value={serverHost}
          onChangeText={setServerHost}
          editable={!discovering}
        />
      </View>

      <View style={styles.section}>
        <Text style={styles.label}>Server Port</Text>
        <TextInput
          style={styles.input}
          placeholder="8000"
          value={serverPort}
          onChangeText={setServerPort}
          keyboardType="number-pad"
          editable={!discovering}
        />
      </View>

      <TouchableOpacity
        style={styles.saveButton}
        onPress={handleSave}
      >
        <Text style={styles.buttonText}>Save Settings</Text>
      </TouchableOpacity>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 16,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 20,
  },
  section: {
    marginBottom: 16,
  },
  label: {
    fontSize: 16,
    marginBottom: 8,
  },
  input: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 4,
    padding: 12,
  },
  button: {
    backgroundColor: '#007AFF',
    padding: 12,
    borderRadius: 4,
    marginBottom: 16,
    alignItems: 'center',
  },
  saveButton: {
    backgroundColor: '#34C759',
    padding: 12,
    borderRadius: 4,
    alignItems: 'center',
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  info: {
    marginBottom: 16,
    padding: 12,
    backgroundColor: '#f0f0f0',
    borderRadius: 4,
  },
});
```

## Integration Steps

1. Copy `MdnsDiscoveryService.kt` to `android/app/src/main/java/com/roommesh/services/`
2. Copy `ServerPreferences.kt` to `android/app/src/main/java/com/roommesh/preferences/`
3. Copy `MdnsModule.kt` to `android/app/src/main/java/com/roommesh/`
4. Register `MdnsModule` in `MainApplication.kt`
5. Copy TypeScript files to the React Native project's `src/` directory
6. Add `androidx.datastore:datastore-preferences` dependency to `build.gradle`
7. Add the Settings screen to the app navigation

## Testing

1. Build and deploy the app to Pixel 7
2. Open Settings screen
3. Tap "Discover Server"
4. Verify the server host and port are populated
5. Test WebRTC signaling with discovered connection
6. Toggle off mDNS and manually enter IP, verify connection still works
