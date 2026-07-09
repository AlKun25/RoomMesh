import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Switch,
  ActivityIndicator,
  ScrollView,
  Alert,
} from 'react-native';
import MdnsDiscovery from '../services/MdnsDiscovery';
import { serverPreferences } from '../services/ServerPreferences';

export const ServerSettingsScreen: React.FC = () => {
  const [mdnsEnabled, setMdnsEnabled] = useState(true);
  const [serverHost, setServerHost] = useState('');
  const [serverPort, setServerPort] = useState('8000');
  const [discovering, setDiscovering] = useState(false);
  const [discoveredHost, setDiscoveredHost] = useState('');
  const [connectionStatus, setConnectionStatus] = useState<
    'idle' | 'testing' | 'success' | 'error'
  >('idle');

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const mdns = await serverPreferences.getMdnsEnabled();
      const host = await serverPreferences.getServerHost();
      const port = await serverPreferences.getServerPort();

      setMdnsEnabled(mdns);
      setServerHost(host);
      setServerPort(port.toString());
    } catch (error) {
      console.error('Error loading settings:', error);
    }
  };

  const handleDiscoverServer = async () => {
    setDiscovering(true);
    setDiscoveredHost('');
    try {
      const result = await MdnsDiscovery.discoverService();
      if (result) {
        setDiscoveredHost(`${result.host}:${result.port}`);
        setServerHost(result.host);
        setServerPort(result.port.toString());
      } else {
        Alert.alert('Discovery Failed', 'Could not find MacBook on the network');
        setDiscoveredHost('Discovery failed');
      }
    } catch (error) {
      console.error('Discovery error:', error);
      Alert.alert('Error', 'An error occurred during discovery');
      setDiscoveredHost('Error');
    } finally {
      setDiscovering(false);
    }
  };

  const handleTestConnection = async () => {
    if (!serverHost) {
      Alert.alert('Error', 'Please enter a server host');
      return;
    }

    setConnectionStatus('testing');
    try {
      const url = `http://${serverHost}:${serverPort}/health`;
      const response = await fetch(url, { timeout: 5000 });

      if (response.ok) {
        setConnectionStatus('success');
        Alert.alert('Success', 'Connected to server successfully');
        setTimeout(() => setConnectionStatus('idle'), 2000);
      } else {
        setConnectionStatus('error');
        Alert.alert('Error', `Server returned status ${response.status}`);
      }
    } catch (error) {
      setConnectionStatus('error');
      Alert.alert(
        'Connection Failed',
        'Could not connect to the server. Please check the host and port.',
      );
      console.error('Connection test error:', error);
    }
  };

  const handleSave = async () => {
    try {
      await serverPreferences.setMdnsEnabled(mdnsEnabled);
      await serverPreferences.setServerHost(serverHost);
      await serverPreferences.setServerPort(parseInt(serverPort, 10));
      Alert.alert('Success', 'Settings saved');
    } catch (error) {
      console.error('Error saving settings:', error);
      Alert.alert('Error', 'Failed to save settings');
    }
  };

  const getConnectionStatusColor = () => {
    switch (connectionStatus) {
      case 'success':
        return '#34C759';
      case 'error':
        return '#FF3B30';
      case 'testing':
        return '#007AFF';
      default:
        return '#888888';
    }
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.content}>
        <Text style={styles.title}>Server Settings</Text>
        <Text style={styles.subtitle}>Configure MacBook connection</Text>

        <View style={styles.section}>
          <View style={styles.switchRow}>
            <Text style={styles.label}>Auto-discover server (mDNS)</Text>
            <Switch
              value={mdnsEnabled}
              onValueChange={setMdnsEnabled}
              trackColor={{ false: '#ccc', true: '#81C784' }}
              thumbColor={mdnsEnabled ? '#4CAF50' : '#999'}
            />
          </View>
          <Text style={styles.description}>
            When enabled, automatically discovers the MacBook on your local network
          </Text>
        </View>

        {mdnsEnabled && (
          <TouchableOpacity
            style={[styles.button, discovering && styles.buttonDisabled]}
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
          <View style={styles.infoBox}>
            <Text style={styles.infoLabel}>Discovered:</Text>
            <Text style={styles.infoValue}>{discoveredHost}</Text>
          </View>
        ) : null}

        <View style={styles.divider} />

        <View style={styles.section}>
          <Text style={styles.label}>Server Host</Text>
          <TextInput
            style={styles.input}
            placeholder="192.168.1.1 or macbook.local"
            placeholderTextColor="#aaa"
            value={serverHost}
            onChangeText={setServerHost}
            editable={!discovering}
            selectTextOnFocus
          />
        </View>

        <View style={styles.section}>
          <Text style={styles.label}>Server Port</Text>
          <TextInput
            style={styles.input}
            placeholder="8000"
            placeholderTextColor="#aaa"
            value={serverPort}
            onChangeText={setServerPort}
            keyboardType="number-pad"
            editable={!discovering}
            selectTextOnFocus
          />
        </View>

        <View style={styles.buttonRow}>
          <TouchableOpacity
            style={[styles.halfButton, styles.testButton]}
            onPress={handleTestConnection}
            disabled={discovering}
          >
            {connectionStatus === 'testing' ? (
              <ActivityIndicator color="#fff" size="small" />
            ) : (
              <Text style={styles.buttonText}>Test Connection</Text>
            )}
          </TouchableOpacity>

          <View style={styles.statusIndicator}>
            <View
              style={[
                styles.statusDot,
                { backgroundColor: getConnectionStatusColor() },
              ]}
            />
            <Text style={styles.statusText}>
              {connectionStatus === 'idle'
                ? 'Not tested'
                : connectionStatus === 'testing'
                  ? 'Testing...'
                  : connectionStatus === 'success'
                    ? 'Connected'
                    : 'Failed'}
            </Text>
          </View>
        </View>

        <TouchableOpacity
          style={[styles.saveButton, discovering && styles.buttonDisabled]}
          onPress={handleSave}
          disabled={discovering}
        >
          <Text style={styles.saveButtonText}>Save Settings</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  content: {
    padding: 16,
  },
  title: {
    fontSize: 28,
    fontWeight: '700',
    marginBottom: 4,
    color: '#1a1a1a',
  },
  subtitle: {
    fontSize: 14,
    color: '#666',
    marginBottom: 24,
  },
  section: {
    marginBottom: 20,
  },
  switchRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  label: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1a1a1a',
    marginBottom: 8,
  },
  description: {
    fontSize: 13,
    color: '#999',
  },
  input: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
    color: '#1a1a1a',
    backgroundColor: '#fff',
  },
  button: {
    backgroundColor: '#007AFF',
    padding: 14,
    borderRadius: 8,
    marginBottom: 16,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 48,
  },
  buttonDisabled: {
    opacity: 0.5,
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  saveButton: {
    backgroundColor: '#34C759',
    padding: 14,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 48,
    marginTop: 8,
  },
  saveButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '700',
  },
  infoBox: {
    backgroundColor: '#E3F2FD',
    padding: 12,
    borderRadius: 8,
    marginBottom: 16,
    borderLeftWidth: 4,
    borderLeftColor: '#007AFF',
  },
  infoLabel: {
    fontSize: 13,
    color: '#666',
    marginBottom: 4,
  },
  infoValue: {
    fontSize: 15,
    fontWeight: '600',
    color: '#007AFF',
  },
  divider: {
    height: 1,
    backgroundColor: '#e0e0e0',
    marginVertical: 20,
  },
  buttonRow: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 16,
    alignItems: 'center',
  },
  halfButton: {
    flex: 1,
    backgroundColor: '#FF9500',
    padding: 12,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 44,
  },
  testButton: {
    backgroundColor: '#FF9500',
  },
  statusIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    flex: 1,
  },
  statusDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
  },
  statusText: {
    fontSize: 13,
    color: '#666',
  },
});
