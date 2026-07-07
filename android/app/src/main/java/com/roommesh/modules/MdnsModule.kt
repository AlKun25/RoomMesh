package com.roommesh.modules

import android.content.Context
import android.net.nsd.NsdManager
import android.net.nsd.NsdServiceInfo
import android.util.Log
import com.facebook.react.bridge.Promise
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReactContextBaseJavaModule
import com.facebook.react.bridge.ReactMethod
import com.facebook.react.bridge.WritableMap
import com.facebook.react.bridge.Arguments
import java.util.concurrent.TimeoutException

class MdnsModule(reactContext: ReactApplicationContext) :
    ReactContextBaseJavaModule(reactContext) {

    private val nsdManager = reactContext.getSystemService(Context.NSD_SERVICE) as NsdManager
    private var discoveryListener: NsdManager.DiscoveryListener? = null
    private var resolveListener: NsdManager.ResolveListener? = null

    override fun getName() = "MdnsModule"

    @ReactMethod
    fun discoverService(serviceName: String, timeout: Int, promise: Promise) {
        Thread {
            try {
                val result = performDiscovery(serviceName, timeout.toLong())
                if (result != null) {
                    promise.resolve(result)
                } else {
                    promise.reject("DISCOVERY_FAILED", "Could not discover service")
                }
            } catch (e: Exception) {
                Log.e(TAG, "Discovery error", e)
                promise.reject("DISCOVERY_ERROR", e.message)
            }
        }.start()
    }

    private fun performDiscovery(
        serviceName: String,
        timeout: Long,
    ): WritableMap? {
        var result: WritableMap? = null
        var discoveryCompleted = false

        discoveryListener = object : NsdManager.DiscoveryListener {
            override fun onServiceFound(serviceInfo: NsdServiceInfo) {
                Log.d(TAG, "Service found: ${serviceInfo.serviceName}")
                if (serviceInfo.serviceName.contains(serviceName)) {
                    resolveListener?.let { return@onServiceFound }
                    resolveService(serviceInfo) { resolved ->
                        result = resolved
                        discoveryCompleted = true
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
                Log.e(TAG, "Discovery failed: $errorCode")
                discoveryCompleted = true
            }

            override fun onStopDiscoveryFailed(serviceType: String, errorCode: Int) {
                Log.e(TAG, "Stop discovery failed: $errorCode")
            }
        }

        try {
            nsdManager.discoverServices(
                "_http._tcp.",
                NsdManager.PROTOCOL_DNS_SD,
                discoveryListener,
            )

            val startTime = System.currentTimeMillis()
            while (!discoveryCompleted && System.currentTimeMillis() - startTime < timeout) {
                Thread.sleep(100)
            }

            discoveryListener?.let {
                try {
                    nsdManager.stopServiceDiscovery(it)
                } catch (e: Exception) {
                    Log.w(TAG, "Error stopping discovery", e)
                }
            }

            return result
        } catch (e: Exception) {
            Log.e(TAG, "Error performing discovery", e)
            discoveryListener?.let {
                try {
                    nsdManager.stopServiceDiscovery(it)
                } catch (stopError: Exception) {
                    Log.w(TAG, "Error stopping discovery after error", stopError)
                }
            }
            return null
        }
    }

    private fun resolveService(
        serviceInfo: NsdServiceInfo,
        callback: (WritableMap?) -> Unit,
    ) {
        resolveListener = object : NsdManager.ResolveListener {
            override fun onServiceResolved(serviceInfo: NsdServiceInfo) {
                Log.d(TAG, "Service resolved: ${serviceInfo.serviceName}")
                val result = Arguments.createMap()
                result.putString("serviceName", serviceInfo.serviceName)
                result.putString("host", serviceInfo.host.hostAddress ?: "localhost")
                result.putInt("port", serviceInfo.port)
                callback(result)
            }

            override fun onResolveFailed(serviceInfo: NsdServiceInfo, errorCode: Int) {
                Log.e(TAG, "Resolve failed: $errorCode")
                callback(null)
            }
        }

        try {
            nsdManager.resolveService(serviceInfo, resolveListener)
        } catch (e: Exception) {
            Log.e(TAG, "Error resolving service", e)
            callback(null)
        }
    }

    @ReactMethod
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
        private const val TAG = "MdnsModule"
    }
}
