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

/** High-level state of the signaling + peer connection, for UI reporting. */
export type ConnectionState =
  | 'idle'
  | 'connecting'
  | 'connected'
  | 'failed'
  | 'closed';

/** Callback invoked whenever the connection state changes. */
export type ConnectionStateListener = (state: ConnectionState) => void;

// Max time to wait for host ICE candidate gathering before sending the offer.
// On a LAN this completes in tens of milliseconds; the cap only guards against
// a stalled interface.
const ICE_GATHERING_TIMEOUT_MS = 5000;

/**
 * Client-side WebRTC service for the RoomMesh connection to the MacBook.
 *
 * It creates an audio-free {@link RTCPeerConnection} with a data channel and
 * performs signaling over a **WebSocket** at `ws://<host>:<port>/signal`
 * (issue #5). No STUN/TURN servers are configured: phone and MacBook are on the
 * same LAN, so host ICE candidates are sufficient.
 *
 * Signaling is **non-trickle**: the server (aiortc) only begins ICE connectivity
 * checks when the remote candidates are present in the offer SDP, so the client
 * waits for ICE gathering to complete and sends a single offer with its
 * candidates embedded. The server likewise embeds its candidates in the answer.
 */
class WebRTCService {
  private pc: RTCPeerConnection | null = null;
  private dataChannel: RTCDataChannel | null = null;
  private ws: WebSocket | null = null;
  private stateListener: ConnectionStateListener | null = null;

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

  /**
   * Establish the WebRTC connection to the MacBook via the `/signal` WebSocket.
   *
   * Waits for ICE gathering to complete, sends the full SDP offer (candidates
   * embedded), applies the server's answer, and reports progress through the
   * optional {@link ConnectionStateListener} until the peer connection reaches
   * `connected`.
   *
   * @param host   Server host (e.g. `macbook.local` or a LAN IP).
   * @param port   Server port (default 8000).
   * @param onState Optional listener for connection-state changes.
   */
  async connect(
    host: string,
    port: number = 8000,
    onState?: ConnectionStateListener,
  ): Promise<void> {
    // Tear down any previous session before starting a new one.
    this.disconnect();
    this.stateListener = onState ?? null;
    this.emitState('connecting');

    const { pc, dataChannel } = await this.createPeerConnection();
    this.pc = pc;
    this.dataChannel = dataChannel;

    pc.addEventListener('connectionstatechange', () => {
      switch (pc.connectionState) {
        case 'connected':
          this.emitState('connected');
          // Signaling is done once the peer link is up; close the socket.
          this.closeSocket();
          break;
        case 'failed':
          this.emitState('failed');
          break;
        case 'closed':
          this.emitState('closed');
          break;
      }
    });

    // Non-trickle: gather all host candidates before sending the offer so the
    // server (aiortc) sees them in the remote description and starts ICE checks.
    await this.waitForIceGatheringComplete(pc);

    const ws = new WebSocket(`ws://${host}:${port}/signal`);
    this.ws = ws;

    ws.onopen = () => {
      // localDescription now carries the gathered candidates.
      ws.send(JSON.stringify({ type: 'offer', sdp: pc.localDescription!.sdp }));
    };

    ws.onmessage = async (event: WebSocketMessageEvent) => {
      try {
        const message = JSON.parse(event.data as string);
        if (message.type === 'answer') {
          await pc.setRemoteDescription(
            new RTCSessionDescription({ type: 'answer', sdp: message.sdp }),
          );
        }
      } catch (error) {
        console.error('WebRTC signaling message error:', error);
        this.emitState('failed');
      }
    };

    ws.onerror = (event: any) => {
      console.error('WebRTC signaling socket error:', event?.message ?? event);
      this.emitState('failed');
    };
  }

  /** Resolve once ICE gathering completes (or a safety timeout elapses). */
  private waitForIceGatheringComplete(pc: RTCPeerConnection): Promise<void> {
    if (pc.iceGatheringState === 'complete') {
      return Promise.resolve();
    }

    return new Promise((resolve) => {
      let settled = false;
      const finish = () => {
        if (settled) {
          return;
        }
        settled = true;
        clearTimeout(timer);
        pc.removeEventListener('icegatheringstatechange', onChange as any);
        pc.removeEventListener('icecandidate', onCandidate as any);
        resolve();
      };

      const onChange = () => {
        if (pc.iceGatheringState === 'complete') {
          finish();
        }
      };
      // A null candidate is the end-of-gathering sentinel.
      const onCandidate = (event: any) => {
        if (!event.candidate) {
          finish();
        }
      };

      const timer = setTimeout(finish, ICE_GATHERING_TIMEOUT_MS);
      pc.addEventListener('icegatheringstatechange', onChange as any);
      pc.addEventListener('icecandidate', onCandidate as any);
    });
  }

  /** Tear down the peer connection, data channel, and signaling socket. */
  disconnect(): void {
    this.closeSocket();

    if (this.dataChannel) {
      try {
        this.dataChannel.close();
      } catch {
        // ignore — channel may already be closed
      }
      this.dataChannel = null;
    }

    if (this.pc) {
      this.pc.close();
      this.pc = null;
    }
  }

  private closeSocket(): void {
    if (this.ws) {
      try {
        this.ws.close();
      } catch {
        // ignore — socket may already be closing
      }
      this.ws = null;
    }
  }

  private emitState(state: ConnectionState): void {
    this.stateListener?.(state);
  }
}

export default new WebRTCService();
