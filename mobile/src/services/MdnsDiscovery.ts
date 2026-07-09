import { Platform } from 'react-native';
import * as Mdns from '../../modules/mdns';
import type { DiscoveryResult } from '../../modules/mdns';

export type { DiscoveryResult };

export interface ServerConfig {
  host: string;
  port: number;
  useMdns: boolean;
}

class MdnsDiscoveryService {
  async discoverService(
    serviceName: string = 'macbook',
    timeout: number = 5000,
  ): Promise<DiscoveryResult | null> {
    if (Platform.OS !== 'android') {
      console.warn('mDNS discovery is only available on Android');
      return null;
    }

    try {
      return await Mdns.discoverService(serviceName, timeout);
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
}

export default new MdnsDiscoveryService();
