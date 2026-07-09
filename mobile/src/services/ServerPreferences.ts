import AsyncStorage from '@react-native-async-storage/async-storage';

const STORAGE_KEYS = {
  MDNS_ENABLED: '@roommesh:mdns_enabled',
  SERVER_HOST: '@roommesh:server_host',
  SERVER_PORT: '@roommesh:server_port',
  LAST_RESOLVED_HOST: '@roommesh:last_resolved_host',
};

export class ServerPreferences {
  async getMdnsEnabled(): Promise<boolean> {
    try {
      const value = await AsyncStorage.getItem(STORAGE_KEYS.MDNS_ENABLED);
      return value === null ? true : value === 'true';
    } catch (error) {
      console.error('Error reading mdns_enabled:', error);
      return true;
    }
  }

  async setMdnsEnabled(enabled: boolean): Promise<void> {
    try {
      await AsyncStorage.setItem(STORAGE_KEYS.MDNS_ENABLED, String(enabled));
    } catch (error) {
      console.error('Error setting mdns_enabled:', error);
    }
  }

  async getServerHost(): Promise<string> {
    try {
      const value = await AsyncStorage.getItem(STORAGE_KEYS.SERVER_HOST);
      return value || '';
    } catch (error) {
      console.error('Error reading server_host:', error);
      return '';
    }
  }

  async setServerHost(host: string): Promise<void> {
    try {
      await AsyncStorage.setItem(STORAGE_KEYS.SERVER_HOST, host);
    } catch (error) {
      console.error('Error setting server_host:', error);
    }
  }

  async getServerPort(): Promise<number> {
    try {
      const value = await AsyncStorage.getItem(STORAGE_KEYS.SERVER_PORT);
      return value ? parseInt(value, 10) : 8000;
    } catch (error) {
      console.error('Error reading server_port:', error);
      return 8000;
    }
  }

  async setServerPort(port: number): Promise<void> {
    try {
      await AsyncStorage.setItem(STORAGE_KEYS.SERVER_PORT, String(port));
    } catch (error) {
      console.error('Error setting server_port:', error);
    }
  }

  async getLastResolvedHost(): Promise<string | null> {
    try {
      return await AsyncStorage.getItem(STORAGE_KEYS.LAST_RESOLVED_HOST);
    } catch (error) {
      console.error('Error reading last_resolved_host:', error);
      return null;
    }
  }

  async setLastResolvedHost(host: string): Promise<void> {
    try {
      await AsyncStorage.setItem(STORAGE_KEYS.LAST_RESOLVED_HOST, host);
    } catch (error) {
      console.error('Error setting last_resolved_host:', error);
    }
  }

  async clearAll(): Promise<void> {
    try {
      await AsyncStorage.multiRemove(Object.values(STORAGE_KEYS));
    } catch (error) {
      console.error('Error clearing preferences:', error);
    }
  }
}

export const serverPreferences = new ServerPreferences();
