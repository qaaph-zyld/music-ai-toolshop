//! Project file format and serialization
//!
//! OpenDAW uses a `.opendaw` directory structure:
//! ```
//! Project.opendaw/
//! |-- project.json      # Tracks, scenes, tempo, settings
//! |-- audio/            # Referenced audio files (copied)
//! |-- samples/          # Recorded takes
//! `-- stems/            # Cached stem separations
//! ```

use crate::{
    DAWError, DAWResult,
    Project, SessionView, Track, TrackType,
    Mixer,
};
use std::path::{Path, PathBuf};
use std::fs;

/// Version of the project file format
pub const PROJECT_FORMAT_VERSION: u32 = 1;

/// Project file manager
pub struct ProjectFile {
    /// Path to the .opendaw directory
    project_path: PathBuf,
    /// Project metadata
    metadata: ProjectMetadata,
}

/// Project metadata for serialization
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ProjectMetadata {
    pub version: u32,
    pub name: String,
    pub created_at: String,
    pub modified_at: String,
    pub sample_rate: u32,
    pub tempo: f32,
    pub time_signature: [u8; 2],
}

/// Serialized project data
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
struct ProjectData {
    metadata: ProjectMetadata,
    tracks: Vec<TrackData>,
    scenes: Vec<SceneData>,
    clips: Vec<ClipData>,
    mixer: MixerData,
    transport: TransportData,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
struct TrackData {
    id: u32,
    name: String,
    track_type: String,
    color: [u8; 3],
    volume_db: f32,
    pan: f32,
    muted: bool,
    soloed: bool,
    armed: bool,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
struct SceneData {
    id: u32,
    name: String,
    color: [u8; 3],
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
struct ClipData {
    id: u32,
    track_id: u32,
    scene_id: u32,
    name: String,
    clip_type: String,
    duration_beats: f32,
    audio_file: Option<String>, // Relative path in audio/ folder
    color: [u8; 3],
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
struct MixerData {
    master_volume_db: f32,
    tracks: Vec<TrackMixerData>,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
struct TrackMixerData {
    track_id: u32,
    volume_db: f32,
    pan: f32,
    muted: bool,
    soloed: bool,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
struct TransportData {
    tempo: f32,
    time_signature: [u8; 2],
    loop_enabled: bool,
    loop_start_beats: f32,
    loop_end_beats: f32,
}

impl ProjectFile {
    /// Create a new project at the given path
    pub fn create(path: &Path, name: &str, sample_rate: u32) -> DAWResult<Self> {
        let project_path = if path.extension().is_none() {
            path.with_extension("opendaw")
        } else {
            path.to_path_buf()
        };

        // Create directory structure
        fs::create_dir_all(&project_path)?;
        fs::create_dir_all(project_path.join("audio"))?;
        fs::create_dir_all(project_path.join("samples"))?;
        fs::create_dir_all(project_path.join("stems"))?;

        let now = chrono::Local::now().to_rfc3339();
        let metadata = ProjectMetadata {
            version: PROJECT_FORMAT_VERSION,
            name: name.to_string(),
            created_at: now.clone(),
            modified_at: now,
            sample_rate,
            tempo: 120.0,
            time_signature: [4, 4],
        };

        let project = Self {
            project_path,
            metadata,
        };

        // Save initial project.json
        project.save_project_json(&ProjectData {
            metadata: project.metadata.clone(),
            tracks: vec![],
            scenes: vec![],
            clips: vec![],
            mixer: MixerData {
                master_volume_db: 0.0,
                tracks: vec![],
            },
            transport: TransportData {
                tempo: 120.0,
                time_signature: [4, 4],
                loop_enabled: false,
                loop_start_beats: 0.0,
                loop_end_beats: 4.0,
            },
        })?;

        Ok(project)
    }

    /// Load an existing project
    pub fn load(path: &Path) -> DAWResult<Self> {
        let project_path = if path.extension().is_none() {
            path.with_extension("opendaw")
        } else {
            path.to_path_buf()
        };

        if !project_path.exists() {
            return Err(DAWError::invalid_param(
                "path",
                project_path.display().to_string(),
                "existing project path"
            ));
        }

        let json_path = project_path.join("project.json");
        let json = fs::read_to_string(&json_path)?;
        let data: ProjectData = serde_json::from_str(&json)?;

        Ok(Self {
            project_path,
            metadata: data.metadata,
        })
    }

    /// Save project from runtime state
    pub fn save_state(&self, project: &Project, _session: &SessionView, _mixer: &Mixer) -> DAWResult<()> {
        let mut data = self.load_project_data()?;

        // Update metadata
        data.metadata.modified_at = chrono::Local::now().to_rfc3339();
        data.metadata.sample_rate = project.sample_rate();
        data.metadata.tempo = project.tempo();

        // Serialize tracks
        data.tracks = project.tracks().iter().enumerate().map(|(i, track)| {
            TrackData {
                id: i as u32,
                name: track.name().to_string(),
                track_type: match track.track_type() {
                    TrackType::Audio => "Audio".to_string(),
                    TrackType::Midi => "Midi".to_string(),
                    TrackType::Group => "Group".to_string(),
                },
                color: [100, 100, 100], // Default gray
                volume_db: 0.0,
                pan: 0.0,
                muted: false,
                soloed: false,
                armed: false,
            }
        }).collect();

        // TODO: Serialize session clips, mixer state, transport state

        self.save_project_json(&data)
    }

    /// Load project into runtime state
    pub fn load_state(&self, project: &mut Project, _session: &mut SessionView) -> DAWResult<()> {
        let data = self.load_project_data()?;

        // Restore project settings
        project.set_name(&data.metadata.name);
        project.set_sample_rate(data.metadata.sample_rate);
        project.set_tempo(data.metadata.tempo);

        // Restore tracks
        project.clear_tracks();
        for track_data in &data.tracks {
            let track_type = match track_data.track_type.as_str() {
                "Midi" => TrackType::Midi,
                "Group" => TrackType::Group,
                _ => TrackType::Audio,
            };
            project.add_track(Track::new(&track_data.name, track_type));
        }

        // TODO: Restore session clips, mixer state

        Ok(())
    }

    /// Import an audio file into the project
    pub fn import_audio(&self, source_path: &Path) -> DAWResult<PathBuf> {
        if !source_path.exists() {
            return Err(DAWError::invalid_param(
                "source_path",
                source_path.display().to_string(),
                "existing file path"
            ));
        }

        let file_name = source_path.file_name()
            .ok_or_else(|| DAWError::invalid_param(
                "source_path",
                source_path.display().to_string(),
                "valid file name"
            ))?;

        let dest_path = self.project_path.join("audio").join(file_name);

        // Copy file to project's audio folder
        fs::copy(source_path, &dest_path)?;

        Ok(dest_path)
    }

    /// Get the path to an audio file within the project
    pub fn get_audio_path(&self, relative_path: &str) -> PathBuf {
        self.project_path.join("audio").join(relative_path)
    }

    /// Get project name
    pub fn name(&self) -> &str {
        &self.metadata.name
    }

    /// Get project path
    pub fn path(&self) -> &Path {
        &self.project_path
    }

    /// Get metadata
    pub fn metadata(&self) -> &ProjectMetadata {
        &self.metadata
    }

    fn load_project_data(&self) -> DAWResult<ProjectData> {
        let json_path = self.project_path.join("project.json");
        let json = fs::read_to_string(&json_path)?;
        let data: ProjectData = serde_json::from_str(&json)?;
        Ok(data)
    }

    fn save_project_json(&self, data: &ProjectData) -> DAWResult<()> {
        let json_path = self.project_path.join("project.json");
        let json = serde_json::to_string_pretty(data)?;
        fs::write(&json_path, json)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::env::temp_dir;

    #[test]
    fn test_project_file_create() {
        let temp_path = temp_dir().join("test_create.opendaw");
        let _ = fs::remove_dir_all(&temp_path);

        let project = ProjectFile::create(&temp_path, "Test Project", 48000).unwrap();

        assert!(temp_path.exists());
        assert!(temp_path.join("audio").exists());
        assert!(temp_path.join("samples").exists());
        assert!(temp_path.join("stems").exists());
        assert!(temp_path.join("project.json").exists());
        assert_eq!(project.name(), "Test Project");

        let _ = fs::remove_dir_all(&temp_path);
    }

    #[test]
    fn test_project_file_save_load() {
        let temp_path = temp_dir().join("test_save_load.opendaw");
        let _ = fs::remove_dir_all(&temp_path);

        // Create and save
        let project_file = ProjectFile::create(&temp_path, "Save Test", 44100).unwrap();
        let mut project = Project::new("Save Test");
        project.set_tempo(128.0);
        project.add_track(Track::new("Drums", TrackType::Audio));
        project.add_track(Track::new("Bass", TrackType::Audio));

        let session = SessionView::new(2, 4);
        let mixer = Mixer::new(2);

        project_file.save_state(&project, &session, &mixer).unwrap();

        // Load back
        let loaded_file = ProjectFile::load(&temp_path).unwrap();
        let mut loaded_project = Project::new("Loaded");
        let mut loaded_session = SessionView::new(2, 4);

        loaded_file.load_state(&mut loaded_project, &mut loaded_session).unwrap();

        assert_eq!(loaded_project.name(), "Save Test");
        assert_eq!(loaded_project.tempo(), 128.0);
        assert_eq!(loaded_project.track_count(), 2);

        let _ = fs::remove_dir_all(&temp_path);
    }

    #[test]
    fn test_import_audio() {
        let temp_path = temp_dir().join("test_audio.opendaw");
        let _ = fs::remove_dir_all(&temp_path);

        let project = ProjectFile::create(&temp_path, "Audio Test", 48000).unwrap();

        // Create a dummy audio file
        let source_file = temp_dir().join("test_audio.wav");
        fs::write(&source_file, "dummy wav data").unwrap();

        let imported = project.import_audio(&source_file).unwrap();

        assert!(imported.exists());
        assert!(imported.to_string_lossy().contains("audio"));

        let _ = fs::remove_file(&source_file);
        let _ = fs::remove_dir_all(&temp_path);
    }
}
