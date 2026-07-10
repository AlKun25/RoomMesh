import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { RTCView, type MediaStream } from 'react-native-webrtc';
import { useRouter } from 'expo-router';
import { startCamera, stopCamera } from '../services/CameraCapture';
import { serverPreferences } from '../services/ServerPreferences';
import WebRTCService, {
  failureReasonLabel,
  type ConnectionState,
  type FailureReason,
} from '../services/WebRTCService';

/**
 * Room-capture screen: previews the back camera and streams it to the MacBook
 * over WebRTC (a video track the server decodes and stores as frames — issue
 * #6). The connection status shows the distinct failure reasons used for
 * real-network testing (issue #7).
 */
export const CaptureScreen: React.FC = () => {
  const router = useRouter();
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [starting, setStarting] = useState(false);
  const [webrtcStatus, setWebrtcStatus] = useState<ConnectionState>('idle');
  const [failureReason, setFailureReason] = useState<FailureReason | null>(null);

  useEffect(() => {
    // Release the camera and tear down the session when leaving the screen.
    return () => {
      WebRTCService.disconnect();
      stopCamera(stream);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stream]);

  const handleStartCamera = async () => {
    setStarting(true);
    try {
      const s = await startCamera();
      setStream(s);
    } catch (error) {
      console.error('Camera start error:', error);
      Alert.alert(
        'Camera Error',
        'Could not start the camera. Check camera permission and try again.',
      );
    } finally {
      setStarting(false);
    }
  };

  const handleStopCamera = () => {
    WebRTCService.disconnect();
    stopCamera(stream);
    setStream(null);
    setWebrtcStatus('idle');
    setFailureReason(null);
  };

  const handleConnectStream = async () => {
    if (!stream) {
      Alert.alert('No Camera', 'Start the camera before streaming.');
      return;
    }

    const host = await serverPreferences.getServerHost();
    const port = await serverPreferences.getServerPort();
    if (!host) {
      Alert.alert(
        'No Server',
        'Configure the MacBook host in Server Settings first.',
      );
      return;
    }

    setFailureReason(null);
    setWebrtcStatus('connecting');
    try {
      await WebRTCService.connect(
        host,
        port,
        (state, reason) => {
          setWebrtcStatus(state);
          if (reason) {
            setFailureReason(reason);
          }
        },
        stream,
      );
    } catch (error) {
      setWebrtcStatus('failed');
      Alert.alert('Stream Failed', 'Could not stream video to the MacBook.');
      console.error('WebRTC stream error:', error);
    }
  };

  const handleDisconnect = () => {
    WebRTCService.disconnect();
    setWebrtcStatus('idle');
    setFailureReason(null);
  };

  const statusColor = () => {
    switch (webrtcStatus) {
      case 'connected':
        return '#34C759';
      case 'failed':
        return '#FF3B30';
      case 'connecting':
        return '#007AFF';
      default:
        return '#888888';
    }
  };

  const statusText = () => {
    switch (webrtcStatus) {
      case 'connecting':
        return 'Connecting…';
      case 'connected':
        return 'Streaming to MacBook';
      case 'failed':
        return failureReason
          ? `Failed — ${failureReasonLabel(failureReason)}`
          : 'Failed';
      case 'closed':
        return 'Closed';
      default:
        return 'Not streaming';
    }
  };

  const isConnected = webrtcStatus === 'connected';

  return (
    <View style={styles.container}>
      <View style={styles.preview}>
        {stream ? (
          <RTCView
            streamURL={stream.toURL()}
            style={styles.rtcView}
            objectFit="cover"
            mirror={false}
          />
        ) : (
          <View style={styles.placeholder}>
            <Text style={styles.placeholderText}>
              Camera off. Tap “Start Camera” to preview.
            </Text>
          </View>
        )}
      </View>

      <View style={styles.controls}>
        <View style={styles.statusRow}>
          <View style={[styles.statusDot, { backgroundColor: statusColor() }]} />
          <Text style={styles.statusText}>{statusText()}</Text>
        </View>

        <TouchableOpacity
          style={[styles.button, styles.cameraButton]}
          onPress={stream ? handleStopCamera : handleStartCamera}
          disabled={starting}
        >
          {starting ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.buttonText}>
              {stream ? 'Stop Camera' : 'Start Camera'}
            </Text>
          )}
        </TouchableOpacity>

        <TouchableOpacity
          style={[
            styles.button,
            styles.streamButton,
            (!stream || webrtcStatus === 'connecting') && styles.buttonDisabled,
          ]}
          onPress={isConnected ? handleDisconnect : handleConnectStream}
          disabled={!stream || webrtcStatus === 'connecting'}
        >
          {webrtcStatus === 'connecting' ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.buttonText}>
              {isConnected ? 'Stop Streaming' : 'Connect & Stream'}
            </Text>
          )}
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.linkButton}
          onPress={() => router.push('/')}
        >
          <Text style={styles.linkText}>Server Settings</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
  },
  preview: {
    flex: 1,
  },
  rtcView: {
    flex: 1,
    backgroundColor: '#000',
  },
  placeholder: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
  },
  placeholderText: {
    color: '#aaa',
    fontSize: 15,
    textAlign: 'center',
  },
  controls: {
    padding: 16,
    backgroundColor: '#111',
  },
  statusRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 12,
  },
  statusDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
  },
  statusText: {
    color: '#eee',
    fontSize: 14,
  },
  button: {
    padding: 14,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 48,
    marginBottom: 12,
  },
  cameraButton: {
    backgroundColor: '#FF9500',
  },
  streamButton: {
    backgroundColor: '#007AFF',
  },
  buttonDisabled: {
    opacity: 0.5,
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  linkButton: {
    alignItems: 'center',
    paddingVertical: 8,
  },
  linkText: {
    color: '#4DA3FF',
    fontSize: 14,
  },
});
