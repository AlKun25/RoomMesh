import { NativeModules, Platform } from 'react-native';

export interface DiscoveryResult {
  serviceName: string;
  host: string;
  port: number;
}

export interface ServerConfig {
  host: string;
  port: number;
  useMdns: boolean;
}

class MdnsDiscoveryService {
  private nativeModule =
    Platform.OS === 'android' ? NativeModules.MdnsModule : null;

  async discoverService(
    serviceName: string = 'macbook',
    timeout: number = 5000,
  ): Promise<DiscoveryResult | null> {
    if (!this.nativeModule) {
      console.warn('mDNS discovery not available on this platform');
      return null;
    }

    try {
      return await this.nativeModule.discoverService(serviceName, timeout);
    } catch (error) {
      console.error('mDNS discovery failed:', error);
      return null;
    }
  }

  async getServerConfig(preferences: any): Promise<ServerConfig> {
    const useMdns = await preferences.getMdnsEnabled();

    if (useMdns) {
      const discovered = await this.discoverService();
      if (discovered) {
        await preferences.setLastResolvedHost(discovered.host);
        return {
          host: discovered.host,
          port: discovered.port,
          useMdns: true,
        };
      }
    }

    const host = await preferences.getServerHost();
    const port = await preferences.getServerPort();

    if (!host) {
      throw new Error('No server configured and mDNS discovery failed');
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
