import { PermissionsAndroid, Platform } from 'react-native';
import { mediaDevices, type MediaStream } from 'react-native-webrtc';

/**
 * Camera capture for RoomMesh, built on `react-native-webrtc`'s `getUserMedia`.
 *
 * We deliberately reuse react-native-webrtc (already a dependency) rather than
 * adding `react-native-vision-camera`: the captured {@link MediaStream} is
 * attached directly to the peer connection as a video track (a MediaChannel),
 * and the MacBook decodes and stores its frames as images for the SfM / 3DGS
 * pipeline. **No audio is captured** — RoomMesh only sends video + data.
 *
 * Finer camera control (exposure/focus lock, ARCore pose per frame) is a later
 * refinement; this service only needs a back-camera video stream.
 */

/** Default capture constraints — back camera, modest resolution/rate for LAN. */
const DEFAULT_CONSTRAINTS = {
  audio: false,
  video: {
    facingMode: 'environment',
    width: 1280,
    height: 720,
    frameRate: 30,
  },
} as const;

/**
 * Request the Android CAMERA runtime permission.
 *
 * On iOS the permission is handled by the OS prompt on first `getUserMedia`
 * (backed by `NSCameraUsageDescription`), so this is a no-op there.
 *
 * @returns `true` if camera access is granted (or not required on this platform).
 */
export async function requestCameraPermission(): Promise<boolean> {
  if (Platform.OS !== 'android') {
    return true;
  }

  const result = await PermissionsAndroid.request(
    PermissionsAndroid.PERMISSIONS.CAMERA,
    {
      title: 'Camera permission',
      message: 'RoomMesh needs the camera to scan the room.',
      buttonPositive: 'Allow',
      buttonNegative: 'Deny',
    },
  );
  return result === PermissionsAndroid.RESULTS.GRANTED;
}

/**
 * Acquire a back-camera video stream (audio disabled).
 *
 * Requests the camera permission first; throws if it is denied so callers can
 * surface a clear error.
 *
 * @returns A {@link MediaStream} with a single video track.
 */
export async function startCamera(): Promise<MediaStream> {
  const granted = await requestCameraPermission();
  if (!granted) {
    throw new Error('Camera permission denied');
  }

  const stream = (await mediaDevices.getUserMedia(
    DEFAULT_CONSTRAINTS,
  )) as MediaStream;
  return stream;
}

/** Stop every track on a capture stream and release the camera. */
export function stopCamera(stream: MediaStream | null): void {
  if (!stream) {
    return;
  }
  stream.getTracks().forEach((track) => {
    try {
      track.stop();
    } catch {
      // ignore — track may already be stopped
    }
  });
}
