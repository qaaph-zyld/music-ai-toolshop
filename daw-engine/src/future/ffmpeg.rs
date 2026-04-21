//! FFmpeg Integration
//!
//! Python bridge to FFmpeg for comprehensive audio/video encoding,
//! decoding, and format conversion. Handles virtually every
//! audio and video format via libavcodec/libavformat.
//!
//! License: LGPL-2.1+ (default)
//! Repo: https://github.com/FFmpeg/FFmpeg

use std::path::Path;
use std::process::Command;

/// FFmpeg error types
#[derive(Debug, Clone, PartialEq)]
pub enum FFmpegError {
    NotFound,
    InvalidInput(String),
    ConversionFailed(String),
    CodecNotSupported(String),
    PythonBridgeError(String),
}

impl std::fmt::Display for FFmpegError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            FFmpegError::NotFound => write!(f, "FFmpeg not found in PATH"),
            FFmpegError::InvalidInput(msg) => write!(f, "Invalid input: {}", msg),
            FFmpegError::ConversionFailed(msg) => write!(f, "Conversion failed: {}", msg),
            FFmpegError::CodecNotSupported(codec) => write!(f, "Codec not supported: {}", codec),
            FFmpegError::PythonBridgeError(msg) => write!(f, "Python bridge error: {}", msg),
        }
    }
}

impl std::error::Error for FFmpegError {}

/// Audio codec enum
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum AudioCodec {
    AAC,
    MP3,
    FLAC,
    Opus,
    Vorbis,
    PCM,
    WAV,
}

impl AudioCodec {
    pub fn as_str(&self) -> &'static str {
        match self {
            AudioCodec::AAC => "aac",
            AudioCodec::MP3 => "libmp3lame",
            AudioCodec::FLAC => "flac",
            AudioCodec::Opus => "libopus",
            AudioCodec::Vorbis => "libvorbis",
            AudioCodec::PCM => "pcm_s16le",
            AudioCodec::WAV => "pcm_s16le",
        }
    }
    
    pub fn extension(&self) -> &'static str {
        match self {
            AudioCodec::AAC => "aac",
            AudioCodec::MP3 => "mp3",
            AudioCodec::FLAC => "flac",
            AudioCodec::Opus => "opus",
            AudioCodec::Vorbis => "ogg",
            AudioCodec::PCM => "raw",
            AudioCodec::WAV => "wav",
        }
    }
}

/// Video codec enum
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum VideoCodec {
    H264,
    H265,
    VP9,
    AV1,
}

impl VideoCodec {
    pub fn as_str(&self) -> &'static str {
        match self {
            VideoCodec::H264 => "libx264",
            VideoCodec::H265 => "libx265",
            VideoCodec::VP9 => "libvpx-vp9",
            VideoCodec::AV1 => "libaom-av1",
        }
    }
}

/// Container format enum
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum ContainerFormat {
    MP4,
    MKV,
    AVI,
    MOV,
    WebM,
    Ogg,
}

impl ContainerFormat {
    pub fn as_str(&self) -> &'static str {
        match self {
            ContainerFormat::MP4 => "mp4",
            ContainerFormat::MKV => "matroska",
            ContainerFormat::AVI => "avi",
            ContainerFormat::MOV => "mov",
            ContainerFormat::WebM => "webm",
            ContainerFormat::Ogg => "ogg",
        }
    }
    
    pub fn extension(&self) -> &'static str {
        match self {
            ContainerFormat::MP4 => "mp4",
            ContainerFormat::MKV => "mkv",
            ContainerFormat::AVI => "avi",
            ContainerFormat::MOV => "mov",
            ContainerFormat::WebM => "webm",
            ContainerFormat::Ogg => "ogg",
        }
    }
}

/// FFmpeg conversion configuration
#[derive(Debug, Clone)]
pub struct ConversionConfig {
    pub audio_codec: Option<AudioCodec>,
    pub video_codec: Option<VideoCodec>,
    pub container: ContainerFormat,
    pub audio_bitrate: Option<u32>, // kbps
    pub video_bitrate: Option<u32>, // kbps
    pub sample_rate: Option<u32>,
    pub channels: Option<u8>,
}

impl Default for ConversionConfig {
    fn default() -> Self {
        Self {
            audio_codec: Some(AudioCodec::AAC),
            video_codec: None,
            container: ContainerFormat::MP4,
            audio_bitrate: Some(192),
            video_bitrate: None,
            sample_rate: Some(44100),
            channels: Some(2),
        }
    }
}

/// Media information
#[derive(Debug, Clone)]
pub struct MediaInfo {
    pub duration_seconds: f64,
    pub format: String,
    pub audio_streams: Vec<AudioStreamInfo>,
    pub video_streams: Vec<VideoStreamInfo>,
}

/// Audio stream information
#[derive(Debug, Clone)]
pub struct AudioStreamInfo {
    pub codec: String,
    pub sample_rate: u32,
    pub channels: u8,
    pub bit_depth: u16,
}

/// Video stream information
#[derive(Debug, Clone)]
pub struct VideoStreamInfo {
    pub codec: String,
    pub width: u32,
    pub height: u32,
    pub fps: f64,
}

/// FFmpeg processor
pub struct FFmpegProcessor;

impl FFmpegProcessor {
    /// Check if FFmpeg is available
    pub fn is_available() -> bool {
        Command::new("ffmpeg")
            .arg("-version")
            .output()
            .map(|output| output.status.success())
            .unwrap_or(false)
    }

    /// Get FFmpeg version
    pub fn version() -> String {
        match Command::new("ffmpeg").arg("-version").output() {
            Ok(output) if output.status.success() => {
                let stdout = String::from_utf8_lossy(&output.stdout);
                stdout.lines().next().unwrap_or("unknown").to_string()
            }
            _ => "not-found".to_string(),
        }
    }

    /// Convert audio/video file
    pub fn convert<P: AsRef<Path>, Q: AsRef<Path>>(
        input: P,
        output: Q,
        config: &ConversionConfig,
    ) -> Result<(), FFmpegError> {
        if !Self::is_available() {
            return Err(FFmpegError::NotFound);
        }

        let mut cmd = Command::new("ffmpeg");
        cmd.arg("-y") // Overwrite output
            .arg("-i")
            .arg(input.as_ref());

        // Audio codec
        if let Some(codec) = &config.audio_codec {
            cmd.arg("-c:a").arg(codec.as_str());
        }

        // Audio bitrate
        if let Some(bitrate) = config.audio_bitrate {
            cmd.arg("-b:a").arg(format!("{}k", bitrate));
        }

        // Video codec
        if let Some(codec) = &config.video_codec {
            cmd.arg("-c:v").arg(codec.as_str());
        }

        // Sample rate
        if let Some(rate) = config.sample_rate {
            cmd.arg("-ar").arg(rate.to_string());
        }

        // Channels
        if let Some(ch) = config.channels {
            cmd.arg("-ac").arg(ch.to_string());
        }

        cmd.arg(output.as_ref());

        match cmd.output() {
            Ok(output) if output.status.success() => Ok(()),
            Ok(output) => {
                let stderr = String::from_utf8_lossy(&output.stderr);
                Err(FFmpegError::ConversionFailed(stderr.to_string()))
            }
            Err(e) => Err(FFmpegError::ConversionFailed(e.to_string())),
        }
    }

    /// Extract audio from video
    pub fn extract_audio<P: AsRef<Path>, Q: AsRef<Path>>(
        video: P,
        audio_output: Q,
        codec: AudioCodec,
    ) -> Result<(), FFmpegError> {
        let config = ConversionConfig {
            audio_codec: Some(codec),
            video_codec: None,
            container: ContainerFormat::from_extension(audio_output.as_ref())
                .unwrap_or(ContainerFormat::MP4),
            ..Default::default()
        };
        Self::convert(video, audio_output, &config)
    }

    /// Get media information
    pub fn probe<P: AsRef<Path>>(path: P) -> Result<MediaInfo, FFmpegError> {
        if !Self::is_available() {
            return Err(FFmpegError::NotFound);
        }

        // TODO: Implement ffprobe integration
        Err(FFmpegError::PythonBridgeError("Probe not implemented yet".to_string()))
    }

    /// Convert to MP3
    pub fn to_mp3<P: AsRef<Path>, Q: AsRef<Path>>(input: P, output: Q, bitrate: u32) -> Result<(), FFmpegError> {
        let config = ConversionConfig {
            audio_codec: Some(AudioCodec::MP3),
            video_codec: None,
            container: ContainerFormat::MP4,
            audio_bitrate: Some(bitrate),
            ..Default::default()
        };
        Self::convert(input, output, &config)
    }

    /// Convert to AAC
    pub fn to_aac<P: AsRef<Path>, Q: AsRef<Path>>(input: P, output: Q, bitrate: u32) -> Result<(), FFmpegError> {
        let config = ConversionConfig {
            audio_codec: Some(AudioCodec::AAC),
            video_codec: None,
            container: ContainerFormat::MP4,
            audio_bitrate: Some(bitrate),
            ..Default::default()
        };
        Self::convert(input, output, &config)
    }
}

impl ContainerFormat {
    fn from_extension<P: AsRef<Path>>(path: P) -> Option<Self> {
        let ext = path.as_ref()
            .extension()
            .and_then(|e| e.to_str())?;
        
        match ext.to_lowercase().as_str() {
            "mp4" | "m4a" => Some(ContainerFormat::MP4),
            "mkv" => Some(ContainerFormat::MKV),
            "avi" => Some(ContainerFormat::AVI),
            "mov" => Some(ContainerFormat::MOV),
            "webm" => Some(ContainerFormat::WebM),
            "ogg" => Some(ContainerFormat::Ogg),
            _ => None,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_ffmpeg_module_exists() {
        let _ = FFmpegError::NotFound;
        let _ = AudioCodec::MP3;
        let _ = VideoCodec::H264;
        let _ = ContainerFormat::MP4;
    }

    #[test]
    fn test_ffmpeg_is_available() {
        let available = FFmpegProcessor::is_available();
        println!("FFmpeg available: {}", available);
    }

    #[test]
    fn test_ffmpeg_version() {
        let version = FFmpegProcessor::version();
        println!("FFmpeg version: {}", version);
    }

    #[test]
    fn test_audio_codec_as_str() {
        assert_eq!(AudioCodec::MP3.as_str(), "libmp3lame");
        assert_eq!(AudioCodec::AAC.as_str(), "aac");
        assert_eq!(AudioCodec::FLAC.as_str(), "flac");
        assert_eq!(AudioCodec::Opus.as_str(), "libopus");
    }

    #[test]
    fn test_audio_codec_extension() {
        assert_eq!(AudioCodec::MP3.extension(), "mp3");
        assert_eq!(AudioCodec::AAC.extension(), "aac");
        assert_eq!(AudioCodec::FLAC.extension(), "flac");
    }

    #[test]
    fn test_video_codec_as_str() {
        assert_eq!(VideoCodec::H264.as_str(), "libx264");
        assert_eq!(VideoCodec::H265.as_str(), "libx265");
        assert_eq!(VideoCodec::VP9.as_str(), "libvpx-vp9");
    }

    #[test]
    fn test_container_format_as_str() {
        assert_eq!(ContainerFormat::MP4.as_str(), "mp4");
        assert_eq!(ContainerFormat::MKV.as_str(), "matroska");
        assert_eq!(ContainerFormat::WebM.as_str(), "webm");
    }

    #[test]
    fn test_conversion_config_defaults() {
        let config = ConversionConfig::default();
        assert_eq!(config.audio_codec, Some(AudioCodec::AAC));
        assert_eq!(config.container, ContainerFormat::MP4);
        assert_eq!(config.audio_bitrate, Some(192));
    }

    #[test]
    fn test_ffmpeg_error_display() {
        let err = FFmpegError::NotFound;
        assert!(err.to_string().contains("not found"));

        let err = FFmpegError::ConversionFailed("test error".to_string());
        assert!(err.to_string().contains("Conversion failed"));
    }

    #[test]
    fn test_container_from_extension() {
        use std::path::PathBuf;
        
        assert_eq!(
            ContainerFormat::from_extension(PathBuf::from("test.mp4")),
            Some(ContainerFormat::MP4)
        );
        assert_eq!(
            ContainerFormat::from_extension(PathBuf::from("test.mkv")),
            Some(ContainerFormat::MKV)
        );
        assert_eq!(
            ContainerFormat::from_extension(PathBuf::from("test.unknown")),
            None
        );
    }
}
