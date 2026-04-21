//! WebRTC Streaming Integration
//!
//! FFI bindings for WebRTC - real-time audio streaming and collaboration
//! Peer-to-peer audio streaming for remote collaboration
//!
//! License: BSD-3-Clause (WebRTC)
//! Repo: https://webrtc.googlesource.com/src/

use std::ffi::{CStr, CString};
use std::os::raw::{c_char, c_int, c_void};
use std::sync::{Arc, Mutex};

/// WebRTC peer connection handle
#[repr(C)]
pub struct WebrtcPeerConnection {
    _private: [u8; 0],
}

/// WebRTC data channel handle
#[repr(C)]
pub struct WebrtcDataChannel {
    _private: [u8; 0],
}

/// WebRTC audio track handle
#[repr(C)]
pub struct WebrtcAudioTrack {
    _private: [u8; 0],
}

/// WebRTC error types
#[derive(Debug, Clone, PartialEq)]
pub enum WebrtcError {
    InitFailed(String),
    ConnectionFailed(String),
    SignalFailed(String),
    DataChannelFailed(String),
    AudioTrackFailed(String),
    NotAvailable,
}

impl std::fmt::Display for WebrtcError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            WebrtcError::InitFailed(msg) => write!(f, "WebRTC init failed: {}", msg),
            WebrtcError::ConnectionFailed(msg) => write!(f, "Connection failed: {}", msg),
            WebrtcError::SignalFailed(msg) => write!(f, "Signaling failed: {}", msg),
            WebrtcError::DataChannelFailed(msg) => write!(f, "Data channel failed: {}", msg),
            WebrtcError::AudioTrackFailed(msg) => write!(f, "Audio track failed: {}", msg),
            WebrtcError::NotAvailable => write!(f, "WebRTC not available"),
        }
    }
}

impl std::error::Error for WebrtcError {}

/// ICE connection state
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum IceConnectionState {
    New,
    Checking,
    Connected,
    Completed,
    Failed,
    Disconnected,
    Closed,
}

/// Peer connection state
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum PeerConnectionState {
    New,
    Connecting,
    Connected,
    Disconnected,
    Failed,
    Closed,
}

/// Signaling state
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum SignalingState {
    Stable,
    HaveLocalOffer,
    HaveLocalPranswer,
    HaveRemoteOffer,
    HaveRemotePranswer,
    Closed,
}

/// Session description type
#[derive(Debug, Clone, PartialEq)]
pub enum SdpType {
    Offer,
    Answer,
    Pranswer,
    Rollback,
}

/// Session description (SDP)
#[derive(Debug, Clone)]
pub struct SessionDescription {
    pub sdp_type: SdpType,
    pub sdp: String,
}

/// ICE candidate
#[derive(Debug, Clone)]
pub struct IceCandidate {
    pub sdp_mid: Option<String>,
    pub sdp_mline_index: Option<u16>,
    pub candidate: String,
}

/// WebRTC configuration
#[derive(Debug, Clone)]
pub struct WebrtcConfig {
    pub stun_servers: Vec<String>,
    pub turn_servers: Vec<(String, String, String)>, // (url, username, password)
    pub enable_audio: bool,
    pub enable_data_channel: bool,
    pub data_channel_label: String,
}

impl Default for WebrtcConfig {
    fn default() -> Self {
        Self {
            stun_servers: vec![
                "stun:stun.l.google.com:19302".to_string(),
                "stun:stun1.l.google.com:19302".to_string(),
            ],
            turn_servers: Vec::new(),
            enable_audio: true,
            enable_data_channel: true,
            data_channel_label: "opendaw-data".to_string(),
        }
    }
}

/// WebRTC streaming engine
pub struct WebrtcStreamEngine {
    peer_connection: *mut WebrtcPeerConnection,
    config: WebrtcConfig,
    local_description: Arc<Mutex<Option<SessionDescription>>>,
    remote_description: Arc<Mutex<Option<SessionDescription>>>,
    ice_candidates: Arc<Mutex<Vec<IceCandidate>>>,
    connection_state: Arc<Mutex<PeerConnectionState>>,
}

/// Audio track wrapper
pub struct WebrtcAudioStream {
    track: *mut WebrtcAudioTrack,
    sample_rate: u32,
    channels: u16,
    track_id: String,
}

/// Data channel wrapper
pub struct WebrtcDataStream {
    channel: *mut WebrtcDataChannel,
    label: String,
    buffered_amount: Arc<Mutex<u32>>,
}

/// Collaboration session info
#[derive(Debug, Clone)]
pub struct CollaborationSession {
    pub session_id: String,
    pub peer_id: String,
    pub peer_name: Option<String>,
    pub latency_ms: u32,
    pub connected_at: std::time::SystemTime,
}

/// Callbacks for WebRTC events
pub struct WebrtcCallbacks {
    pub on_ice_candidate: Option<Box<dyn Fn(IceCandidate) + Send>>,
    pub on_connection_state_change: Option<Box<dyn Fn(PeerConnectionState) + Send>>,
    pub on_data_channel_message: Option<Box<dyn Fn(Vec<u8>) + Send>>,
    pub on_audio_data: Option<Box<dyn Fn(&[f32]) + Send>>,
}

impl Default for WebrtcCallbacks {
    fn default() -> Self {
        Self {
            on_ice_candidate: None,
            on_connection_state_change: None,
            on_data_channel_message: None,
            on_audio_data: None,
        }
    }
}

// FFI function declarations
extern "C" {
    fn webrtc_ffi_is_available() -> c_int;
    fn webrtc_ffi_get_version() -> *const c_char;
    
    // Peer connection
    fn webrtc_ffi_create_peer_connection(config_json: *const c_char) -> *mut WebrtcPeerConnection;
    fn webrtc_ffi_destroy_peer_connection(pc: *mut WebrtcPeerConnection);
    fn webrtc_ffi_create_offer(pc: *mut WebrtcPeerConnection, sdp_out: *mut c_char, sdp_size: c_int) -> c_int;
    fn webrtc_ffi_create_answer(pc: *mut WebrtcPeerConnection, sdp_out: *mut c_char, sdp_size: c_int) -> c_int;
    fn webrtc_ffi_set_local_description(pc: *mut WebrtcPeerConnection, 
                                          sdp_type: *const c_char, sdp: *const c_char) -> c_int;
    fn webrtc_ffi_set_remote_description(pc: *mut WebrtcPeerConnection,
                                         sdp_type: *const c_char, sdp: *const c_char) -> c_int;
    fn webrtc_ffi_add_ice_candidate(pc: *mut WebrtcPeerConnection,
                                    sdp_mid: *const c_char, mline_index: c_int,
                                    candidate: *const c_char) -> c_int;
    fn webrtc_ffi_get_connection_state(pc: *mut WebrtcPeerConnection) -> c_int;
    fn webrtc_ffi_get_signaling_state(pc: *mut WebrtcPeerConnection) -> c_int;
    fn webrtc_ffi_get_ice_connection_state(pc: *mut WebrtcPeerConnection) -> c_int;
    
    // Audio
    fn webrtc_ffi_create_audio_track(pc: *mut WebrtcPeerConnection, 
                                      track_id: *const c_char,
                                      sample_rate: c_int, channels: c_int) -> *mut WebrtcAudioTrack;
    fn webrtc_ffi_destroy_audio_track(track: *mut WebrtcAudioTrack);
    fn webrtc_ffi_send_audio(track: *mut WebrtcAudioTrack, 
                              samples: *const f32, sample_count: c_int) -> c_int;
    fn webrtc_ffi_set_remote_audio_callback(track: *mut WebrtcAudioTrack,
                                               callback: *mut c_void) -> c_int;
    
    // Data channel
    fn webrtc_ffi_create_data_channel(pc: *mut WebrtcPeerConnection,
                                       label: *const c_char) -> *mut WebrtcDataChannel;
    fn webrtc_ffi_destroy_data_channel(channel: *mut WebrtcDataChannel);
    fn webrtc_ffi_send_data(channel: *mut WebrtcDataChannel,
                            data: *const c_char, length: c_int) -> c_int;
    fn webrtc_ffi_set_data_callback(channel: *mut WebrtcDataChannel,
                                    callback: *mut c_void) -> c_int;
    fn webrtc_ffi_get_buffered_amount(channel: *mut WebrtcDataChannel) -> c_int;
    
    // Callbacks
    fn webrtc_ffi_set_ice_candidate_callback(pc: *mut WebrtcPeerConnection,
                                             callback: *mut c_void) -> c_int;
    fn webrtc_ffi_set_connection_state_callback(pc: *mut WebrtcPeerConnection,
                                                 callback: *mut c_void) -> c_int;
}

impl WebrtcStreamEngine {
    /// Create new WebRTC streaming engine
    pub fn new(config: WebrtcConfig) -> Result<Self, WebrtcError> {
        if !Self::is_available() {
            return Err(WebrtcError::NotAvailable);
        }

        let config_json = Self::build_config_json(&config);
        let config_cstring = CString::new(config_json)
            .map_err(|e| WebrtcError::InitFailed(e.to_string()))?;

        unsafe {
            let pc = webrtc_ffi_create_peer_connection(config_cstring.as_ptr());
            if pc.is_null() {
                return Err(WebrtcError::InitFailed(
                    "Failed to create peer connection".to_string()
                ));
            }

            Ok(Self {
                peer_connection: pc,
                config,
                local_description: Arc::new(Mutex::new(None)),
                remote_description: Arc::new(Mutex::new(None)),
                ice_candidates: Arc::new(Mutex::new(Vec::new())),
                connection_state: Arc::new(Mutex::new(PeerConnectionState::New)),
            })
        }
    }

    /// Check if WebRTC is available
    pub fn is_available() -> bool {
        unsafe { webrtc_ffi_is_available() != 0 }
    }

    /// Get WebRTC version
    pub fn version() -> String {
        unsafe {
            let version_ptr = webrtc_ffi_get_version();
            if version_ptr.is_null() {
                return "unknown".to_string();
            }
            CStr::from_ptr(version_ptr)
                .to_string_lossy()
                .into_owned()
        }
    }

    /// Create offer (initiator side)
    pub fn create_offer(&mut self) -> Result<SessionDescription, WebrtcError> {
        const SDP_SIZE: usize = 8192;
        let mut sdp_buffer = vec![0i8; SDP_SIZE];

        unsafe {
            let result = webrtc_ffi_create_offer(
                self.peer_connection,
                sdp_buffer.as_mut_ptr() as *mut c_char,
                SDP_SIZE as c_int,
            );

            if result != 0 {
                return Err(WebrtcError::SignalFailed(
                    format!("Create offer failed: {}", result)
                ));
            }

            let sdp = CStr::from_ptr(sdp_buffer.as_ptr() as *const c_char)
                .to_string_lossy()
                .into_owned();

            let desc = SessionDescription {
                sdp_type: SdpType::Offer,
                sdp,
            };

            *self.local_description.lock().unwrap() = Some(desc.clone());
            Ok(desc)
        }
    }

    /// Create answer (responder side)
    pub fn create_answer(&mut self) -> Result<SessionDescription, WebrtcError> {
        const SDP_SIZE: usize = 8192;
        let mut sdp_buffer = vec![0i8; SDP_SIZE];

        unsafe {
            let result = webrtc_ffi_create_answer(
                self.peer_connection,
                sdp_buffer.as_mut_ptr() as *mut c_char,
                SDP_SIZE as c_int,
            );

            if result != 0 {
                return Err(WebrtcError::SignalFailed(
                    format!("Create answer failed: {}", result)
                ));
            }

            let sdp = CStr::from_ptr(sdp_buffer.as_ptr() as *const c_char)
                .to_string_lossy()
                .into_owned();

            let desc = SessionDescription {
                sdp_type: SdpType::Answer,
                sdp,
            };

            *self.local_description.lock().unwrap() = Some(desc.clone());
            Ok(desc)
        }
    }

    /// Set local description
    pub fn set_local_description(&mut self, desc: &SessionDescription) 
        -> Result<(), WebrtcError> {
        let type_cstring = CString::new(format!("{:?}", desc.sdp_type).to_lowercase())
            .map_err(|e| WebrtcError::SignalFailed(e.to_string()))?;
        let sdp_cstring = CString::new(desc.sdp.clone())
            .map_err(|e| WebrtcError::SignalFailed(e.to_string()))?;

        unsafe {
            let result = webrtc_ffi_set_local_description(
                self.peer_connection,
                type_cstring.as_ptr(),
                sdp_cstring.as_ptr(),
            );

            if result != 0 {
                return Err(WebrtcError::SignalFailed(
                    format!("Set local description failed: {}", result)
                ));
            }

            *self.local_description.lock().unwrap() = Some(desc.clone());
            Ok(())
        }
    }

    /// Set remote description
    pub fn set_remote_description(&mut self, desc: &SessionDescription) 
        -> Result<(), WebrtcError> {
        let type_cstring = CString::new(format!("{:?}", desc.sdp_type).to_lowercase())
            .map_err(|e| WebrtcError::SignalFailed(e.to_string()))?;
        let sdp_cstring = CString::new(desc.sdp.clone())
            .map_err(|e| WebrtcError::SignalFailed(e.to_string()))?;

        unsafe {
            let result = webrtc_ffi_set_remote_description(
                self.peer_connection,
                type_cstring.as_ptr(),
                sdp_cstring.as_ptr(),
            );

            if result != 0 {
                return Err(WebrtcError::SignalFailed(
                    format!("Set remote description failed: {}", result)
                ));
            }

            *self.remote_description.lock().unwrap() = Some(desc.clone());
            Ok(())
        }
    }

    /// Add ICE candidate
    pub fn add_ice_candidate(&mut self, candidate: &IceCandidate) 
        -> Result<(), WebrtcError> {
        let sdp_mid_cstring = candidate.sdp_mid.as_ref()
            .map(|s| CString::new(s.as_str()).ok())
            .flatten();
        let candidate_cstring = CString::new(candidate.candidate.clone())
            .map_err(|e| WebrtcError::SignalFailed(e.to_string()))?;

        let sdp_mid_ptr = sdp_mid_cstring.as_ref()
            .map(|cs| cs.as_ptr())
            .unwrap_or(std::ptr::null());
        let mline_index = candidate.sdp_mline_index.unwrap_or(0) as c_int;

        unsafe {
            let result = webrtc_ffi_add_ice_candidate(
                self.peer_connection,
                sdp_mid_ptr,
                mline_index,
                candidate_cstring.as_ptr(),
            );

            if result != 0 {
                return Err(WebrtcError::SignalFailed(
                    format!("Add ICE candidate failed: {}", result)
                ));
            }

            self.ice_candidates.lock().unwrap().push(candidate.clone());
            Ok(())
        }
    }

    /// Get connection state
    pub fn connection_state(&self) -> PeerConnectionState {
        *self.connection_state.lock().unwrap()
    }

    /// Get signaling state from native
    pub fn signaling_state(&self) -> SignalingState {
        unsafe {
            let state = webrtc_ffi_get_signaling_state(self.peer_connection);
            match state {
                0 => SignalingState::Stable,
                1 => SignalingState::HaveLocalOffer,
                2 => SignalingState::HaveLocalPranswer,
                3 => SignalingState::HaveRemoteOffer,
                4 => SignalingState::HaveRemotePranswer,
                _ => SignalingState::Closed,
            }
        }
    }

    /// Get ICE connection state
    pub fn ice_connection_state(&self) -> IceConnectionState {
        unsafe {
            let state = webrtc_ffi_get_ice_connection_state(self.peer_connection);
            match state {
                0 => IceConnectionState::New,
                1 => IceConnectionState::Checking,
                2 => IceConnectionState::Connected,
                3 => IceConnectionState::Completed,
                4 => IceConnectionState::Failed,
                5 => IceConnectionState::Disconnected,
                _ => IceConnectionState::Closed,
            }
        }
    }

    /// Create audio track for streaming
    pub fn create_audio_track(&mut self, track_id: &str, sample_rate: u32, channels: u16) 
        -> Result<WebrtcAudioStream, WebrtcError> {
        let track_id_cstring = CString::new(track_id)
            .map_err(|e| WebrtcError::AudioTrackFailed(e.to_string()))?;

        unsafe {
            let track = webrtc_ffi_create_audio_track(
                self.peer_connection,
                track_id_cstring.as_ptr(),
                sample_rate as c_int,
                channels as c_int,
            );

            if track.is_null() {
                return Err(WebrtcError::AudioTrackFailed(
                    "Failed to create audio track".to_string()
                ));
            }

            Ok(WebrtcAudioStream {
                track,
                sample_rate,
                channels,
                track_id: track_id.to_string(),
            })
        }
    }

    /// Create data channel
    pub fn create_data_channel(&mut self, label: &str) 
        -> Result<WebrtcDataStream, WebrtcError> {
        let label_cstring = CString::new(label)
            .map_err(|e| WebrtcError::DataChannelFailed(e.to_string()))?;

        unsafe {
            let channel = webrtc_ffi_create_data_channel(self.peer_connection, label_cstring.as_ptr());
            if channel.is_null() {
                return Err(WebrtcError::DataChannelFailed(
                    "Failed to create data channel".to_string()
                ));
            }

            Ok(WebrtcDataStream {
                channel,
                label: label.to_string(),
                buffered_amount: Arc::new(Mutex::new(0)),
            })
        }
    }

    fn build_config_json(config: &WebrtcConfig) -> String {
        let stun_servers: Vec<String> = config.stun_servers.iter()
            .map(|s| format!("\\\"{}\\\"", s))
            .collect();
        
        let servers = stun_servers.join(",");
        format!("{{\"iceServers\":[{{\"urls\":[{}]}}]}}", servers)
    }
}

impl Drop for WebrtcStreamEngine {
    fn drop(&mut self) {
        unsafe {
            if !self.peer_connection.is_null() {
                webrtc_ffi_destroy_peer_connection(self.peer_connection);
            }
        }
    }
}

impl WebrtcAudioStream {
    /// Send audio samples
    pub fn send(&mut self, samples: &[f32]) -> Result<(), WebrtcError> {
        unsafe {
            let result = webrtc_ffi_send_audio(
                self.track,
                samples.as_ptr(),
                samples.len() as c_int,
            );

            if result != 0 {
                return Err(WebrtcError::AudioTrackFailed(
                    format!("Send audio failed: {}", result)
                ));
            }

            Ok(())
        }
    }

    /// Get track ID
    pub fn track_id(&self) -> &str {
        &self.track_id
    }

    /// Get sample rate
    pub fn sample_rate(&self) -> u32 {
        self.sample_rate
    }

    /// Get channel count
    pub fn channels(&self) -> u16 {
        self.channels
    }
}

impl Drop for WebrtcAudioStream {
    fn drop(&mut self) {
        unsafe {
            if !self.track.is_null() {
                webrtc_ffi_destroy_audio_track(self.track);
            }
        }
    }
}

impl WebrtcDataStream {
    /// Send data message
    pub fn send(&mut self, data: &[u8]) -> Result<(), WebrtcError> {
        unsafe {
            // Convert to string for FFI (base64 or raw bytes)
            let data_str = base64_encode(data);
            let data_cstring = CString::new(data_str)
                .map_err(|e| WebrtcError::DataChannelFailed(e.to_string()))?;

            let result = webrtc_ffi_send_data(
                self.channel,
                data_cstring.as_ptr(),
                data.len() as c_int,
            );

            if result != 0 {
                return Err(WebrtcError::DataChannelFailed(
                    format!("Send data failed: {}", result)
                ));
            }

            Ok(())
        }
    }

    /// Get buffered amount
    pub fn buffered_amount(&self) -> u32 {
        *self.buffered_amount.lock().unwrap()
    }

    /// Get channel label
    pub fn label(&self) -> &str {
        &self.label
    }
}

impl Drop for WebrtcDataStream {
    fn drop(&mut self) {
        unsafe {
            if !self.channel.is_null() {
                webrtc_ffi_destroy_data_channel(self.channel);
            }
        }
    }
}

/// Simple base64 encoding (for data channel FFI)
fn base64_encode(data: &[u8]) -> String {
    const ALPHABET: &[u8] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let mut result = String::new();
    
    for chunk in data.chunks(3) {
        let b1 = chunk.get(0).copied().unwrap_or(0);
        let b2 = chunk.get(1).copied().unwrap_or(0);
        let b3 = chunk.get(2).copied().unwrap_or(0);
        
        result.push(ALPHABET[((b1 >> 2) & 0x3F) as usize] as char);
        result.push(ALPHABET[(((b1 << 4) | (b2 >> 4)) & 0x3F) as usize] as char);
        
        if chunk.len() > 1 {
            result.push(ALPHABET[(((b2 << 2) | (b3 >> 6)) & 0x3F) as usize] as char);
        } else {
            result.push('=');
        }
        
        if chunk.len() > 2 {
            result.push(ALPHABET[(b3 & 0x3F) as usize] as char);
        } else {
            result.push('=');
        }
    }
    
    result
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_webrtc_module_exists() {
        let _ = WebrtcError::NotAvailable;
        let _ = IceConnectionState::New;
        let _ = PeerConnectionState::Connecting;
        let _ = SdpType::Offer;
        let _ = WebrtcConfig::default();
    }

    #[test]
    fn test_webrtc_is_available() {
        let available = WebrtcStreamEngine::is_available();
        println!("WebRTC available: {}", available);
    }

    #[test]
    fn test_webrtc_version() {
        let version = WebrtcStreamEngine::version();
        println!("WebRTC version: {}", version);
    }

    #[test]
    fn test_ice_connection_states() {
        let states = vec![
            IceConnectionState::New,
            IceConnectionState::Checking,
            IceConnectionState::Connected,
            IceConnectionState::Completed,
            IceConnectionState::Failed,
            IceConnectionState::Disconnected,
            IceConnectionState::Closed,
        ];
        for state in states {
            let s = format!("{:?}", state);
            assert!(!s.is_empty());
        }
    }

    #[test]
    fn test_peer_connection_states() {
        let states = vec![
            PeerConnectionState::New,
            PeerConnectionState::Connecting,
            PeerConnectionState::Connected,
            PeerConnectionState::Disconnected,
            PeerConnectionState::Failed,
            PeerConnectionState::Closed,
        ];
        for state in states {
            let s = format!("{:?}", state);
            assert!(!s.is_empty());
        }
    }

    #[test]
    fn test_sdp_types() {
        let types = vec![
            SdpType::Offer,
            SdpType::Answer,
            SdpType::Pranswer,
            SdpType::Rollback,
        ];
        for t in types {
            let s = format!("{:?}", t);
            assert!(!s.is_empty());
        }
    }

    #[test]
    fn test_webrtc_config_default() {
        let config = WebrtcConfig::default();
        assert!(!config.stun_servers.is_empty());
        assert!(config.turn_servers.is_empty());
        assert!(config.enable_audio);
        assert!(config.enable_data_channel);
        assert_eq!(config.data_channel_label, "opendaw-data");
    }

    #[test]
    fn test_session_description() {
        let desc = SessionDescription {
            sdp_type: SdpType::Offer,
            sdp: "v=0\r\n...".to_string(),
        };
        assert_eq!(desc.sdp_type, SdpType::Offer);
        assert_eq!(desc.sdp, "v=0\r\n...");
    }

    #[test]
    fn test_ice_candidate() {
        let candidate = IceCandidate {
            sdp_mid: Some("0".to_string()),
            sdp_mline_index: Some(0),
            candidate: "candidate:1 1 UDP 2130706431 192.168.1.1 5000 typ host".to_string(),
        };
        assert_eq!(candidate.sdp_mid, Some("0".to_string()));
        assert_eq!(candidate.sdp_mline_index, Some(0));
    }

    #[test]
    fn test_webrtc_error_display() {
        let err = WebrtcError::NotAvailable;
        assert!(err.to_string().contains("not available"));

        let err = WebrtcError::InitFailed("test".to_string());
        assert!(err.to_string().contains("init failed"));

        let err = WebrtcError::ConnectionFailed("test".to_string());
        assert!(err.to_string().contains("Connection failed"));

        let err = WebrtcError::SignalFailed("test".to_string());
        assert!(err.to_string().contains("Signaling failed"));

        let err = WebrtcError::DataChannelFailed("test".to_string());
        assert!(err.to_string().contains("Data channel failed"));

        let err = WebrtcError::AudioTrackFailed("test".to_string());
        assert!(err.to_string().contains("Audio track failed"));
    }

    #[test]
    fn test_collaboration_session() {
        let session = CollaborationSession {
            session_id: "sess-123".to_string(),
            peer_id: "peer-456".to_string(),
            peer_name: Some("Alice".to_string()),
            latency_ms: 45,
            connected_at: std::time::SystemTime::now(),
        };
        
        assert_eq!(session.session_id, "sess-123");
        assert_eq!(session.latency_ms, 45);
    }

    #[test]
    fn test_base64_encode() {
        let data = b"Hello, World!";
        let encoded = base64_encode(data);
        assert!(!encoded.is_empty());
        assert!(encoded.chars().all(|c| c.is_ascii_alphanumeric() || c == '+' || c == '/' || c == '='));
    }

    #[test]
    fn test_stream_accessors() {
        let audio_stream = WebrtcAudioStream {
            track: std::ptr::null_mut(),
            sample_rate: 48000,
            channels: 2,
            track_id: "audio-1".to_string(),
        };
        
        assert_eq!(audio_stream.sample_rate(), 48000);
        assert_eq!(audio_stream.channels(), 2);
        assert_eq!(audio_stream.track_id(), "audio-1");

        let data_stream = WebrtcDataStream {
            channel: std::ptr::null_mut(),
            label: "test-channel".to_string(),
            buffered_amount: Arc::new(Mutex::new(1024)),
        };
        
        assert_eq!(data_stream.label(), "test-channel");
        assert_eq!(data_stream.buffered_amount(), 1024);
    }
}
