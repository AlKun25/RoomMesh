import { requireNativeModule } from 'expo-modules-core';

export interface DiscoveryResult {
  serviceName: string;
  host: string;
  port: number;
}

// Native module registered by MdnsModule.kt as Name("Mdns"). Android-only.
const MdnsNativeModule = requireNativeModule('Mdns');

/**
 * Discover an `_http._tcp.` service on the local network whose name contains
 * `serviceName`. Resolves to the service's host/port, or `null` if none is
 * found within `timeout` milliseconds.
 */
export async function discoverService(
  serviceName: string,
  timeout: number,
): Promise<DiscoveryResult | null> {
  return await MdnsNativeModule.discoverService(serviceName, timeout);
}
