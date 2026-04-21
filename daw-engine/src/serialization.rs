//! Project Serialization
//!
//! JSON serialization for OpenDAW projects with full state preservation.

use serde::{Serialize, Deserialize};

use crate::transport::{Transport, PlayMode};
use crate::session::SessionView;
use crate::mixer::Mixer;
use crate::project::Project;

/// Project file format version
pub const PROJECT_VERSION: &str = "1.0";

/// Serializable project structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SerializableProject {
    pub version: String,
    pub project: ProjectInfo,
    pub transport: SerializableTransportState,
    pub session: SessionState,
    pub mixer: MixerState,
}

/// Project metadata
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProjectInfo {
    pub name: String,
    pub created_at: String,
    pub modified_at: String,
}

/// Serializable transport state
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SerializableTransportState {
    pub tempo: f32,
    pub position_beats: f32,
    pub state: crate::transport::TransportState,
    pub play_mode: PlayMode,
    pub loop_start: f32,
    pub loop_end: f32,
    pub punch_in: Option<f32>,
    pub punch_out: Option<f32>,
}

/// Session state for serialization
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SessionState {
    pub tracks: usize,
    pub scenes: usize,
    pub clips: Vec<ClipInfo>,
}

/// Clip information for serialization
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClipInfo {
    pub track: usize,
    pub scene: usize,
    pub name: String,
    pub duration_bars: f32,
    pub clip_type: String, // "audio" or "midi"
}

/// Mixer state for serialization
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MixerState {
    pub channels: usize,
    pub tracks: Vec<TrackState>,
}

/// Individual track state
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TrackState {
    pub index: usize,
    pub name: String,
    pub volume_db: f32,
    pub pan: f32,
    pub mute: bool,
    pub solo: bool,
}

/// Serialization error types
#[derive(Debug)]
pub enum SerializationError {
    JsonError(serde_json::Error),
    IoError(std::io::Error),
    VersionMismatch { expected: String, found: String },
}

impl std::fmt::Display for SerializationError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            SerializationError::JsonError(e) => write!(f, "JSON error: {}", e),
            SerializationError::IoError(e) => write!(f, "IO error: {}", e),
            SerializationError::VersionMismatch { expected, found } => {
                write!(f, "Version mismatch: expected {}, found {}", expected, found)
            }
        }
    }
}

impl std::error::Error for SerializationError {}

impl From<serde_json::Error> for SerializationError {
    fn from(e: serde_json::Error) -> Self {
        SerializationError::JsonError(e)
    }
}

impl From<std::io::Error> for SerializationError {
    fn from(e: std::io::Error) -> Self {
        SerializationError::IoError(e)
    }
}

/// Serialize project to JSON string
pub fn project_to_json(project: &Project, transport: &Transport, session: &SessionView, mixer: &Mixer) -> Result<String, SerializationError> {
    let serializable = SerializableProject {
        version: PROJECT_VERSION.to_string(),
        project: ProjectInfo {
            name: project.name().to_string(),
            created_at: chrono::Utc::now().to_rfc3339(),
            modified_at: chrono::Utc::now().to_rfc3339(),
        },
        transport: SerializableTransportState {
            tempo: transport.tempo(),
            position_beats: transport.position_beats(),
            state: transport.state(),
            play_mode: transport.play_mode(),
            loop_start: transport.loop_range().0,
            loop_end: transport.loop_range().1,
            punch_in: None, // TODO: Add punch-in/out to transport API
            punch_out: None,
        },
        session: SessionState {
            tracks: session.track_count(),
            scenes: session.scene_count(),
            clips: extract_clips(session),
        },
        mixer: MixerState {
            channels: mixer.source_count(),
            tracks: extract_track_states(mixer),
        },
    };
    
    serde_json::to_string_pretty(&serializable).map_err(|e| e.into())
}

/// Deserialize project from JSON string
pub fn project_from_json(json: &str) -> Result<SerializableProject, SerializationError> {
    let project: SerializableProject = serde_json::from_str(json)?;
    
    // Validate version
    if project.version != PROJECT_VERSION {
        return Err(SerializationError::VersionMismatch {
            expected: PROJECT_VERSION.to_string(),
            found: project.version,
        });
    }
    
    Ok(project)
}

/// Parse version string into (major, minor, patch) tuple
pub fn parse_version(version: &str) -> (u32, u32, u32) {
    let parts: Vec<&str> = version.split('.').collect();
    let major = parts.get(0).and_then(|s| s.parse().ok()).unwrap_or(0);
    let minor = parts.get(1).and_then(|s| s.parse().ok()).unwrap_or(0);
    let patch = parts.get(2).and_then(|s| s.parse().ok()).unwrap_or(0);
    (major, minor, patch)
}

/// Check if a project version is compatible with current engine version
/// 
/// Compatibility rules:
/// - Same major and minor version: fully compatible
/// - Same major, higher patch: compatible (backward compatible fixes)
/// - Same major, higher minor: not compatible (new features may break)
/// - Higher major: not compatible (breaking changes)
pub fn is_version_compatible(engine_version: &str, project_version: &str) -> bool {
    let (eng_major, eng_minor, _eng_patch) = parse_version(engine_version);
    let (proj_major, proj_minor, _proj_patch) = parse_version(project_version);
    
    // Major version must match exactly
    if proj_major != eng_major {
        return false;
    }
    
    // Minor version: project must be <= engine version
    // (engine can load older projects, but not newer ones with new features)
    if proj_minor > eng_minor {
        return false;
    }
    
    // Patch version: any patch is compatible within same major.minor
    // Patch versions are just bug fixes
    true
}

/// Check if a project version can be migrated to current version
/// 
/// Migration rules:
/// - Can migrate from any older version to current
/// - Cannot migrate from newer versions (future)
/// - Major version changes are allowed if migrating forward
fn can_migrate_to_current(project_version: &str) -> bool {
    let (proj_major, proj_minor, _proj_patch) = parse_version(project_version);
    let (curr_major, curr_minor, _curr_patch) = parse_version(PROJECT_VERSION);
    
    // Can migrate if project version is older than current
    if proj_major < curr_major {
        return true;
    }
    if proj_major == curr_major && proj_minor < curr_minor {
        return true;
    }
    // Same version or newer - no migration needed or can't migrate from future
    false
}

/// Load project with automatic version migration
/// 
/// Attempts to migrate older project versions to the current version.
/// Returns error if project version is too new or incompatible.
pub fn load_project_with_migration(json: &str) -> Result<SerializableProject, SerializationError> {
    let mut project: SerializableProject = serde_json::from_str(json)?;
    let project_version = project.version.clone();
    
    // Check if already current version
    if project_version == PROJECT_VERSION {
        return Ok(project);
    }
    
    // Check if version can be migrated (must be older than current)
    if !can_migrate_to_current(&project_version) {
        return Err(SerializationError::VersionMismatch {
            expected: PROJECT_VERSION.to_string(),
            found: project_version,
        });
    }
    
    // Perform migration from older version
    migrate_project(&mut project, &project_version)?;
    
    // Update version to current
    project.version = PROJECT_VERSION.to_string();
    
    Ok(project)
}

/// Migrate project from old version to current version
fn migrate_project(project: &mut SerializableProject, from_version: &str) -> Result<(), SerializationError> {
    let (major, minor, _patch) = parse_version(from_version);
    
    // Migration from 0.9 to 1.0
    if major == 0 && minor == 9 {
        // In version 0.9, transport didn't have punch_in/punch_out
        // They were added in 1.0, so we need to initialize them
        if project.transport.punch_in.is_none() {
            project.transport.punch_in = None;
        }
        if project.transport.punch_out.is_none() {
            project.transport.punch_out = None;
        }
        
        // Update modified timestamp
        project.project.modified_at = chrono::Utc::now().to_rfc3339();
        
        return Ok(());
    }
    
    // Unknown old version - cannot migrate
    Err(SerializationError::VersionMismatch {
        expected: PROJECT_VERSION.to_string(),
        found: from_version.to_string(),
    })
}

/// Record a version change in project history
/// 
/// This is a placeholder for future version history tracking
pub fn record_version_change(_project: &mut SerializableProject, _from_version: &str, _change_note: &str) {
    // Future implementation could track version history in project metadata
    // For now, this is a no-op as the version is already updated
}

/// Extract clip information from session
fn extract_clips(session: &SessionView) -> Vec<ClipInfo> {
    let mut clips = Vec::new();
    
    for track_idx in 0..session.track_count() {
        for scene_idx in 0..session.scene_count() {
            if let Some(clip) = session.get_clip(track_idx, scene_idx) {
                clips.push(ClipInfo {
                    track: track_idx,
                    scene: scene_idx,
                    name: clip.name().to_string(),
                    duration_bars: clip.duration_bars(),
                    clip_type: if clip.is_audio() { "audio".to_string() } else { "midi".to_string() },
                });
            }
        }
    }
    
    clips
}

/// Extract track states from mixer
fn extract_track_states(mixer: &Mixer) -> Vec<TrackState> {
    // For now, create placeholder track states
    // Full implementation would require track metadata in mixer
    (0..mixer.source_count())
        .map(|i| TrackState {
            index: i,
            name: format!("Track {}", i + 1),
            volume_db: 0.0,
            pan: 0.0,
            mute: false,
            solo: false,
        })
        .collect()
}

/// Save project to file
pub fn save_project_to_file(
    project: &Project,
    transport: &Transport,
    session: &SessionView,
    mixer: &Mixer,
    path: &std::path::Path,
) -> Result<(), SerializationError> {
    let json = project_to_json(project, transport, session, mixer)?;
    std::fs::write(path, json)?;
    Ok(())
}

/// Load project from file
pub fn load_project_from_file(path: &std::path::Path) -> Result<SerializableProject, SerializationError> {
    let json = std::fs::read_to_string(path)?;
    project_from_json(&json)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;

    #[test]
    fn test_transport_serialization_roundtrip() {
        let transport = crate::transport::Transport::new(128.0, 48000);
        
        let state = SerializableTransportState {
            tempo: transport.tempo(),
            position_beats: transport.position_beats(),
            state: transport.state(),
            play_mode: transport.play_mode(),
            loop_start: transport.loop_range().0,
            loop_end: transport.loop_range().1,
            punch_in: None,
            punch_out: None,
        };
        
        let json = serde_json::to_string(&state).unwrap();
        let deserialized: SerializableTransportState = serde_json::from_str(&json).unwrap();
        
        assert_eq!(deserialized.tempo, 128.0);
        assert_eq!(deserialized.position_beats, 0.0);
        assert_eq!(deserialized.state, crate::transport::TransportState::Stopped);
    }

    #[test]
    fn test_session_serialization() {
        let session = SessionView::new(8, 16);
        let state = SessionState {
            tracks: session.track_count(),
            scenes: session.scene_count(),
            clips: extract_clips(&session),
        };
        
        let json = serde_json::to_string(&state).unwrap();
        let deserialized: SessionState = serde_json::from_str(&json).unwrap();
        
        assert_eq!(deserialized.tracks, 8);
        assert_eq!(deserialized.scenes, 16);
        assert!(deserialized.clips.is_empty());
    }

    #[test]
    fn test_clip_info_serialization() {
        let clip_info = ClipInfo {
            track: 0,
            scene: 0,
            name: "Test Clip".to_string(),
            duration_bars: 4.0,
            clip_type: "audio".to_string(),
        };
        
        let json = serde_json::to_string(&clip_info).unwrap();
        let deserialized: ClipInfo = serde_json::from_str(&json).unwrap();
        
        assert_eq!(deserialized.track, 0);
        assert_eq!(deserialized.scene, 0);
        assert_eq!(deserialized.name, "Test Clip");
        assert_eq!(deserialized.duration_bars, 4.0);
        assert_eq!(deserialized.clip_type, "audio");
    }

    #[test]
    fn test_mixer_state_serialization() {
        let mixer = Mixer::new(2);
        let state = MixerState {
            channels: mixer.source_count(),
            tracks: extract_track_states(&mixer),
        };
        
        let json = serde_json::to_string(&state).unwrap();
        let deserialized: MixerState = serde_json::from_str(&json).unwrap();
        
        assert_eq!(deserialized.channels, 0); // No sources added yet
        assert!(deserialized.tracks.is_empty());
    }

    #[test]
    fn test_project_info_serialization() {
        let info = ProjectInfo {
            name: "My Song".to_string(),
            created_at: chrono::Utc::now().to_rfc3339(),
            modified_at: chrono::Utc::now().to_rfc3339(),
        };
        
        let json = serde_json::to_string(&info).unwrap();
        let deserialized: ProjectInfo = serde_json::from_str(&json).unwrap();
        
        assert_eq!(deserialized.name, "My Song");
    }

    #[test]
    fn test_save_and_load_project() {
        let project = Project::new("Test Project");
        let transport = crate::transport::Transport::new(120.0, 48000);
        let session = SessionView::new(4, 8);
        let mixer = Mixer::new(2);
        
        // Create temp file
        let mut temp_file = tempfile::NamedTempFile::with_suffix(".opendaw").unwrap();
        let path = temp_file.path().to_path_buf();
        
        // Save project
        save_project_to_file(&project, &transport, &session, &mixer, &path).unwrap();
        
        // Load project
        let loaded = load_project_from_file(&path).unwrap();
        
        assert_eq!(loaded.project.name, "Test Project");
        assert_eq!(loaded.transport.tempo, 120.0);
        assert_eq!(loaded.session.tracks, 4);
        assert_eq!(loaded.session.scenes, 8);
    }

    #[test]
    fn test_version_mismatch_detection() {
        let json = r#"{"version": "0.5", "project": {"name": "Test", "created_at": "", "modified_at": ""}, "transport": {"tempo": 120.0, "position_beats": 0.0, "state": "Stopped", "play_mode": "OneShot", "loop_start": 0.0, "loop_end": 4.0, "punch_in": null, "punch_out": null}, "session": {"tracks": 4, "scenes": 8, "clips": []}, "mixer": {"channels": 0, "tracks": []}}"#;
        
        let result = project_from_json(json);
        assert!(result.is_err());
        
        match result {
            Err(SerializationError::VersionMismatch { expected, found }) => {
                assert_eq!(expected, PROJECT_VERSION);
                assert_eq!(found, "0.5");
            }
            _ => panic!("Expected version mismatch error"),
        }
    }

    #[test]
    fn test_invalid_json_handling() {
        let result = project_from_json("not valid json");
        assert!(result.is_err());
    }

    #[test]
    fn test_track_state_serialization() {
        let track = TrackState {
            index: 0,
            name: "Kick".to_string(),
            volume_db: -6.0,
            pan: 0.0,
            mute: false,
            solo: false,
        };
        
        let json = serde_json::to_string(&track).unwrap();
        let deserialized: TrackState = serde_json::from_str(&json).unwrap();
        
        assert_eq!(deserialized.index, 0);
        assert_eq!(deserialized.name, "Kick");
        assert_eq!(deserialized.volume_db, -6.0);
        assert_eq!(deserialized.pan, 0.0);
        assert!(!deserialized.mute);
        assert!(!deserialized.solo);
    }

    #[test]
    fn test_serialization_error_display() {
        let json_err = serde_json::from_str::<SerializableProject>("invalid").unwrap_err();
        let err = SerializationError::JsonError(json_err);
        
        let display = format!("{}", err);
        assert!(display.contains("JSON error"));
    }

    #[test]
    fn test_project_version_compatibility() {
        // Test that 1.0 projects are compatible with 1.0
        assert!(is_version_compatible("1.0", "1.0"));
        
        // Test that 1.0 can read 1.0.x patch versions
        assert!(is_version_compatible("1.0", "1.0.1"));
        assert!(is_version_compatible("1.0", "1.0.5"));
        
        // Test that 1.0 cannot read 1.1 (minor version bump = potential breaking changes)
        assert!(!is_version_compatible("1.0", "1.1"));
        
        // Test that 1.0 cannot read 2.0 (major version bump = breaking changes)
        assert!(!is_version_compatible("1.0", "2.0"));
    }

    #[test]
    fn test_version_parsing() {
        assert_eq!(parse_version("1.0"), (1, 0, 0));
        assert_eq!(parse_version("2.5.3"), (2, 5, 3));
        assert_eq!(parse_version("1.0.0"), (1, 0, 0));
    }

    #[test]
    fn test_load_with_version_migration() {
        // Create an old version 0.9 project JSON
        let old_project_json = r#"{
            "version": "0.9",
            "project": {"name": "Legacy Project", "created_at": "2024-01-01T00:00:00Z", "modified_at": "2024-01-01T00:00:00Z"},
            "transport": {"tempo": 120.0, "position_beats": 0.0, "state": "Stopped", "play_mode": "OneShot", "loop_start": 0.0, "loop_end": 4.0, "punch_in": null, "punch_out": null},
            "session": {"tracks": 4, "scenes": 8, "clips": []},
            "mixer": {"channels": 0, "tracks": []}
        }"#;
        
        // Should migrate from 0.9 to 1.0
        let result = load_project_with_migration(old_project_json);
        assert!(result.is_ok());
        
        let migrated = result.unwrap();
        assert_eq!(migrated.version, PROJECT_VERSION);
        assert_eq!(migrated.project.name, "Legacy Project");
    }

    #[test]
    fn test_unsupported_version_rejection() {
        // Version 2.0 is not yet supported (future version)
        let future_project_json = r#"{
            "version": "2.0",
            "project": {"name": "Future Project", "created_at": "2026-01-01T00:00:00Z", "modified_at": "2026-01-01T00:00:00Z"},
            "transport": {"tempo": 140.0, "position_beats": 0.0, "state": "Stopped", "play_mode": "OneShot", "loop_start": 0.0, "loop_end": 8.0, "punch_in": null, "punch_out": null},
            "session": {"tracks": 16, "scenes": 32, "clips": []},
            "mixer": {"channels": 0, "tracks": []}
        }"#;
        
        let result = load_project_with_migration(future_project_json);
        assert!(result.is_err());
        
        match result {
            Err(SerializationError::VersionMismatch { expected, found }) => {
                assert_eq!(expected, PROJECT_VERSION);
                assert_eq!(found, "2.0");
            }
            _ => panic!("Expected version mismatch for unsupported future version"),
        }
    }

    #[test]
    fn test_project_version_history() {
        let mut project = SerializableProject {
            version: PROJECT_VERSION.to_string(),
            project: ProjectInfo {
                name: "Test".to_string(),
                created_at: chrono::Utc::now().to_rfc3339(),
                modified_at: chrono::Utc::now().to_rfc3339(),
            },
            transport: SerializableTransportState {
                tempo: 120.0,
                position_beats: 0.0,
                state: crate::transport::TransportState::Stopped,
                play_mode: PlayMode::OneShot,
                loop_start: 0.0,
                loop_end: 4.0,
                punch_in: None,
                punch_out: None,
            },
            session: SessionState {
                tracks: 4,
                scenes: 8,
                clips: vec![],
            },
            mixer: MixerState {
                channels: 2,
                tracks: vec![],
            },
        };
        
        // Record version history
        record_version_change(&mut project, "1.0", "Updated project structure");
        
        // Version should remain current
        assert_eq!(project.version, PROJECT_VERSION);
    }
}
