import {
  RTCPeerConnection,
  RTCSessionDescription,
} from 'react-native-webrtc';

// react-native-webrtc does not re-export the RTCDataChannel type from its entry
// point, so derive it from createDataChannel's return type.
type RTCDataChannel = ReturnType<RTCPeerConnection['createDataChannel']>;

/**
 * A WebRTC peer connection plus its outbound data channel and initial SDP offer.
 */
export interface PeerConnection {
  pc: RTCPeerConnection;
  dataChannel: RTCDataChannel;
  offer: RTCSessionDescription;
}

/**
 * Client-side WebRTC scaffolding for the RoomMesh connection to the MacBook.
 *
 * This mirrors the server's audio-free peer connection: it creates an
 * {@link RTCPeerConnection} with a data channel and generates an SDP offer, but
 * adds **no audio track**. It intentionally does NOT perform signaling — posting
 * the offer to the server's `/signal` endpoint, applying the answer, and
 * exchanging ICE candidates is wired up in issue #5.
 */
class WebRTCService {
  /**
   * Build an audio-free peer connection with a data channel and an SDP offer.
   *
   * No STUN/TURN servers are configured: phone and MacBook are on the same LAN,
   * so host ICE candidates are sufficient.
   */
  async createPeerConnection(label: string = 'roommesh'): Promise<PeerConnection> {
    // Empty ICE server list — local-network only (no STUN/TURN needed).
    const pc = new RTCPeerConnection({ iceServers: [] });

    // Data (not media) path: SCTP data channels need no codec negotiation.
    const dataChannel = pc.createDataChannel(label);

    // No audio track is added — RoomMesh only sends data/video to the MacBook.
    const offer = await pc.createOffer({});
    await pc.setLocalDescription(offer);

    return {
      pc,
      dataChannel,
      offer: new RTCSessionDescription(pc.localDescription!),
    };
  }

  // TODO(issue #5): exchange the offer/answer over macbook.local:8000/signal
  //   - POST `offer` to the signaling endpoint and await the SDP answer
  //   - pc.setRemoteDescription(answer)
  //   - gather and exchange ICE candidates (pc.onicecandidate / addIceCandidate)
}

export default new WebRTCService();
