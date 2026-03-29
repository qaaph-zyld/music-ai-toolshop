//! Session view
//! 
//! Ableton Live-style clip slot grid with scene launch functionality.

/// Clip playback state
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum ClipState {
    /// Clip is stopped
    Stopped,
    /// Clip is queued to play on next beat
    Queued,
    /// Clip is currently playing
    Playing,
    /// Clip is recording
    Recording,
}

impl Default for ClipState {
    fn default() -> Self {
        ClipState::Stopped
    }
}

/// Audio or MIDI clip
#[derive(Debug, Clone)]
pub struct Clip {
    name: String,
    duration_bars: f32,
    state: ClipState,
    is_audio: bool,
}

impl Clip {
    /// Create new audio clip
    pub fn new_audio(name: &str, duration_bars: f32) -> Self {
        Self {
            name: name.to_string(),
            duration_bars,
            state: ClipState::Stopped,
            is_audio: true,
        }
    }
    
    /// Create new MIDI clip
    pub fn new_midi(name: &str, duration_bars: f32) -> Self {
        Self {
            name: name.to_string(),
            duration_bars,
            state: ClipState::Stopped,
            is_audio: false,
        }
    }
    
    /// Get clip name
    pub fn name(&self) -> &str {
        &self.name
    }
    
    /// Get duration in bars
    pub fn duration_bars(&self) -> f32 {
        self.duration_bars
    }
    
    /// Get current state
    pub fn state(&self) -> ClipState {
        self.state
    }
    
    /// Start playback
    pub fn play(&mut self) {
        self.state = ClipState::Playing;
    }
    
    /// Stop playback
    pub fn stop(&mut self) {
        self.state = ClipState::Stopped;
    }
    
    /// Queue for playback
    pub fn queue(&mut self) {
        self.state = ClipState::Queued;
    }
    
    /// Check if clip is audio
    pub fn is_audio(&self) -> bool {
        self.is_audio
    }
    
    /// Check if clip is MIDI
    pub fn is_midi(&self) -> bool {
        !self.is_audio
    }
}

/// Scene (horizontal row in session grid)
#[derive(Debug)]
pub struct Scene {
    clips: Vec<Option<Clip>>,
    name: String,
}

impl Scene {
    fn new(track_count: usize, name: String) -> Self {
        Self {
            clips: vec![None; track_count],
            name,
        }
    }
    
    fn launch(&mut self) {
        for clip in &mut self.clips {
            if let Some(ref mut c) = clip {
                c.play();
            }
        }
    }
    
    fn stop(&mut self) {
        for clip in &mut self.clips {
            if let Some(ref mut c) = clip {
                c.stop();
            }
        }
    }
    
    fn playing_clips(&self) -> Vec<&Clip> {
        self.clips
            .iter()
            .filter_map(|c| c.as_ref())
            .filter(|c| c.state == ClipState::Playing)
            .collect()
    }
}

/// Session view (clip slot grid)
#[derive(Debug)]
pub struct SessionView {
    tracks: usize,
    scenes: Vec<Scene>,
    current_scene: Option<usize>,
}

impl SessionView {
    /// Create new session view
    pub fn new(tracks: usize, scene_count: usize) -> Self {
        let scenes: Vec<Scene> = (0..scene_count)
            .map(|i| Scene::new(tracks, format!("Scene {}", i + 1)))
            .collect();
        
        Self {
            tracks,
            scenes,
            current_scene: None,
        }
    }
    
    /// Get track count
    pub fn track_count(&self) -> usize {
        self.tracks
    }
    
    /// Get scene count
    pub fn scene_count(&self) -> usize {
        self.scenes.len()
    }
    
    /// Get clip at track/scene position
    pub fn get_clip(&self, track: usize, scene: usize) -> Option<&Clip> {
        self.scenes.get(scene)?.clips.get(track)?.as_ref()
    }
    
    /// Get mutable clip reference
    fn get_clip_mut(&mut self, track: usize, scene: usize) -> Option<&mut Clip> {
        self.scenes.get_mut(scene)?.clips.get_mut(track)?.as_mut()
    }
    
    /// Set clip at position
    pub fn set_clip(&mut self, track: usize, scene: usize, clip: Clip) {
        if let Some(s) = self.scenes.get_mut(scene) {
            if track < s.clips.len() {
                s.clips[track] = Some(clip);
            }
        }
    }
    
    /// Launch a scene (row)
    pub fn launch_scene(&mut self, scene_index: usize) {
        // Stop current scene if different
        if let Some(current) = self.current_scene {
            if current != scene_index {
                if let Some(s) = self.scenes.get_mut(current) {
                    s.stop();
                }
            }
        }
        
        // Launch new scene
        if let Some(s) = self.scenes.get_mut(scene_index) {
            s.launch();
        }
        
        self.current_scene = Some(scene_index);
    }
    
    /// Stop all clips
    pub fn stop_all(&mut self) {
        for scene in &mut self.scenes {
            scene.stop();
        }
        self.current_scene = None;
    }
    
    /// Get all currently playing clips
    pub fn get_playing_clips(&self) -> Vec<&Clip> {
        self.scenes
            .iter()
            .flat_map(|s| s.playing_clips())
            .collect()
    }
    
    /// Get current scene index
    pub fn current_scene(&self) -> Option<usize> {
        self.current_scene
    }
}
