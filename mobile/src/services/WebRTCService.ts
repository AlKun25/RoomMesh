import {
  RTCPeerConnection,
  RTCSessionDescription,
  type MediaStream,
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

/**
 * Why a connection attempt failed, so real-network testing (issue #7) can tell
 * the failure modes apart instead of collapsing them all into `'failed'`:
 * - `ws-unreachable`  — the `/signal` WebSocket never opened (wrong host, phone
 *   on a different network/cellular, firewall).
 * - `ice-failed`      — signaling succeeded but the peers never connected (AP
 *   isolation, multicast/UDP blocked between devices).
 * - `signaling-error` — a malformed/unexpected signaling message.
 * (`mdns-timeout` is reported by the discovery layer, not here.)
 */
export type FailureReason =
  | 'ws-unreachable'
  | 'ice-failed'
  | 'signaling-error';

/** Human-readable label for a {@link FailureReason}, for status lines. */
export function failureReasonLabel(reason: FailureReason): string {
  switch (reason) {
    case 'ws-unreachable':
      return 'server unreachable (ws)';
    case 'ice-failed':
      return 'peer connection failed (ice)';
    case 'signaling-error':
      return 'signaling error';
    default:
      return reason;
  }
}

/**
 * Callback invoked whenever the connection state changes. On `'failed'` a
 * {@link FailureReason} is provided when known.
 */
export type ConnectionStateListener = (
  state: ConnectionState,
  reason?: FailureReason,
) => void;

// Max time to wait for host ICE candidate gathering before sending the offer.
// On a LAN this completes in tens of milliseconds; the cap only guards against
// a stalled interface.
const ICE_GATHERING_TIMEOUT_MS = 5000;

/**
 * Client-side WebRTC service for the RoomMesh connection to the MacBook.
 *
 * It creates an {@link RTCPeerConnection} with a data channel and, when a camera
 * stream is supplied, a **video track** (a MediaChannel the MacBook decodes and
 * stores as frames — issue #6). The connection is **audio-free**: RoomMesh only
 * sends video + data. Signaling runs over a **WebSocket** at
 * `ws://<host>:<port>/signal` (issue #5). No STUN/TURN servers are configured:
 * phone and MacBook are on the same LAN, so host ICE candidates are sufficient.
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
  private failureReason: FailureReason | null = null;
  // True once the server's SDP answer has been applied. Used to attribute a
  // socket failure to `ws-unreachable` (before answer) vs an ICE failure after.
  private answered = false;

  /**
   * Build a peer connection with a data channel — plus a video track when a
   * camera `stream` is supplied — and an SDP offer.
   *
   * No STUN/TURN servers are configured: phone and MacBook are on the same LAN,
   * so host ICE candidates are sufficient. No audio is ever added.
   *
   * @param label  Data-channel label.
   * @param stream Optional camera {@link MediaStream}; its video track is added
   *               to the connection so frames stream to the MacBook.
   */
  async createPeerConnection(
    label: string = 'roommesh',
    stream?: MediaStream,
  ): Promise<PeerConnection> {
    // Empty ICE server list — local-network only (no STUN/TURN needed).
    const pc = new RTCPeerConnection({ iceServers: [] });

    // Data path: SCTP data channel (reserved for future control/pose messages).
    const dataChannel = pc.createDataChannel(label);

    // Video (no audio): add the camera track so the offer carries an m=video
    // section the MacBook can decode into stored frames.
    if (stream) {
      stream
        .getVideoTracks()
        .forEach((track) => pc.addTrack(track, stream));
    }

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
   * @param stream Optional camera {@link MediaStream} to stream to the MacBook.
   */
  async connect(
    host: string,
    port: number = 8000,
    onState?: ConnectionStateListener,
    stream?: MediaStream,
  ): Promise<void> {
    // Tear down any previous session before starting a new one.
    this.disconnect();
    this.stateListener = onState ?? null;
    this.answered = false;
    this.emitState('connecting');

    const { pc, dataChannel } = await this.createPeerConnection('roommesh', stream);
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
          // Signaling worked (or we'd be ws-unreachable) but the peers never
          // connected — the classic AP-isolation / UDP-blocked failure mode.
          this.emitState('failed', 'ice-failed');
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
          this.answered = true;
        }
      } catch (error) {
        console.error('WebRTC signaling message error:', error);
        this.emitState('failed', 'signaling-error');
      }
    };

    ws.onerror = (event: any) => {
      console.error('WebRTC signaling socket error:', event?.message ?? event);
      // Before the answer, a socket error means we never reached the server.
      // After it, the peer link takes over and reports ICE state separately.
      if (!this.answered) {
        this.emitState('failed', 'ws-unreachable');
      }
    };

    ws.onclose = (event: any) => {
      // A close before the handshake completes (and while not yet connected) is
      // the server being unreachable, not a normal post-connect socket close.
      if (!this.answered && this.pc?.connectionState !== 'connected') {
        console.error('WebRTC signaling socket closed early:', event?.code);
        this.emitState('failed', 'ws-unreachable');
      }
    };
  }

  /** The reason for the most recent failure, if known (issue #7 diagnostics). */
  get lastFailureReason(): FailureReason | null {
    return this.failureReason;
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
      // Detach handlers first so our own close() doesn't fire onclose/onerror
      // and get misread as an unreachable-server failure.
      this.ws.onopen = null;
      this.ws.onmessage = null;
      this.ws.onerror = null;
      this.ws.onclose = null;
      try {
        this.ws.close();
      } catch {
        // ignore — socket may already be closing
      }
      this.ws = null;
    }
  }

  private emitState(state: ConnectionState, reason?: FailureReason): void {
    this.failureReason = state === 'failed' ? (reason ?? null) : null;
    this.stateListener?.(state, reason);
  }
}

export default new WebRTCService();
