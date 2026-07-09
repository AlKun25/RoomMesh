package expo.modules.mdns

import android.content.Context
import android.net.nsd.NsdManager
import android.net.nsd.NsdServiceInfo
import android.os.Handler
import android.os.Looper
import android.util.Log
import expo.modules.kotlin.Promise
import expo.modules.kotlin.exception.Exceptions
import expo.modules.kotlin.modules.Module
import expo.modules.kotlin.modules.ModuleDefinition
import java.util.concurrent.atomic.AtomicBoolean

// mDNS / Bonjour service discovery, exposed to JS as `requireNativeModule('Mdns')`.
// Discovers `_http._tcp.` services on the local network and resolves the first one
// whose name contains the requested service name (e.g. "macbook").
class MdnsModule : Module() {
  private val context: Context
    get() = appContext.reactContext ?: throw Exceptions.ReactContextLost()

  private val nsdManager: NsdManager
    get() = context.getSystemService(Context.NSD_SERVICE) as NsdManager

  private var discoveryListener: NsdManager.DiscoveryListener? = null
  private var isResolving = false

  override fun definition() = ModuleDefinition {
    Name("Mdns")

    AsyncFunction("discoverService") { serviceName: String, timeout: Int, promise: Promise ->
      startDiscovery(serviceName, timeout.toLong(), promise)
    }

    OnDestroy {
      stopDiscovery()
    }
  }

  private fun startDiscovery(serviceName: String, timeout: Long, promise: Promise) {
    val manager = nsdManager
    val settled = AtomicBoolean(false)
    isResolving = false

    val listener = object : NsdManager.DiscoveryListener {
      override fun onServiceFound(serviceInfo: NsdServiceInfo) {
        Log.d(TAG, "Service found: ${serviceInfo.serviceName}")
        if (serviceInfo.serviceName.contains(serviceName) && !isResolving && !settled.get()) {
          isResolving = true
          resolveService(manager, serviceInfo) { result ->
            isResolving = false
            if (result != null && settled.compareAndSet(false, true)) {
              stopDiscovery()
              promise.resolve(result)
            }
          }
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
        Log.e(TAG, "Start discovery failed: $errorCode")
        if (settled.compareAndSet(false, true)) {
          promise.reject("DISCOVERY_FAILED", "Failed to start discovery (code $errorCode)", null)
        }
      }

      override fun onStopDiscoveryFailed(serviceType: String, errorCode: Int) {
        Log.w(TAG, "Stop discovery failed: $errorCode")
      }
    }
    discoveryListener = listener

    try {
      manager.discoverServices("_http._tcp.", NsdManager.PROTOCOL_DNS_SD, listener)
    } catch (e: Exception) {
      Log.e(TAG, "Error starting discovery", e)
      if (settled.compareAndSet(false, true)) {
        promise.reject("DISCOVERY_ERROR", e.message, e)
      }
      return
    }

    // Resolve with null (not found) once the timeout elapses.
    Handler(Looper.getMainLooper()).postDelayed({
      if (settled.compareAndSet(false, true)) {
        stopDiscovery()
        promise.resolve(null)
      }
    }, timeout)
  }

  private fun resolveService(
    manager: NsdManager,
    serviceInfo: NsdServiceInfo,
    callback: (Map<String, Any>?) -> Unit,
  ) {
    val resolveListener = object : NsdManager.ResolveListener {
      override fun onServiceResolved(info: NsdServiceInfo) {
        Log.d(TAG, "Service resolved: ${info.serviceName}")
        callback(
          mapOf(
            "serviceName" to info.serviceName,
            "host" to (info.host?.hostAddress ?: "localhost"),
            "port" to info.port,
          )
        )
      }

      override fun onResolveFailed(info: NsdServiceInfo, errorCode: Int) {
        Log.e(TAG, "Resolve failed: $errorCode")
        callback(null)
      }
    }

    try {
      manager.resolveService(serviceInfo, resolveListener)
    } catch (e: Exception) {
      Log.e(TAG, "Error resolving service", e)
      callback(null)
    }
  }

  private fun stopDiscovery() {
    discoveryListener?.let {
      try {
        nsdManager.stopServiceDiscovery(it)
      } catch (e: Exception) {
        Log.w(TAG, "Error stopping discovery", e)
      }
    }
    discoveryListener = null
  }

  companion object {
    private const val TAG = "MdnsModule"
  }
}
