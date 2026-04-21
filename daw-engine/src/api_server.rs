//! HTTP API Server for OpenDAW
//!
//! Provides REST endpoints for the Suno Library browser and other DAW features.

use axum::{
    extract::{Query, State},
    http::StatusCode,
    response::Json,
    routing::{get, post},
    Router,
};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tower_http::cors::{Any, CorsLayer};

use crate::ai_bridge::{AIBridge, SunoTrack};

/// API server state
pub struct ApiState {
    ai_bridge: AIBridge,
}

impl ApiState {
    pub fn new() -> Self {
        Self {
            ai_bridge: AIBridge::new(),
        }
    }
}

/// Track response structure
#[derive(Debug, Serialize)]
pub struct TracksResponse {
    pub tracks: Vec<SunoTrack>,
    pub count: usize,
}

/// Search query parameters
#[derive(Debug, Deserialize)]
pub struct SearchQuery {
    pub q: Option<String>,
    pub genre: Option<String>,
    pub tempo_min: Option<u32>,
    pub tempo_max: Option<u32>,
}

/// Import request
#[derive(Debug, Deserialize)]
pub struct ImportRequest {
    pub track_id: String,
    pub target_track: usize,
    pub target_scene: usize,
}

/// Import response
#[derive(Debug, Serialize)]
pub struct ImportResponse {
    pub success: bool,
    pub message: String,
}

/// Get all tracks handler
async fn get_tracks(State(state): State<Arc<ApiState>>) -> Result<Json<TracksResponse>, StatusCode> {
    match state.ai_bridge.search_suno_library(None, None, None, None) {
        Ok(tracks) => {
            let count = tracks.len();
            Ok(Json(TracksResponse { tracks, count }))
        }
        Err(_) => Err(StatusCode::INTERNAL_SERVER_ERROR),
    }
}

/// Search tracks handler
async fn search_tracks(
    State(state): State<Arc<ApiState>>,
    Query(query): Query<SearchQuery>,
) -> Result<Json<TracksResponse>, StatusCode> {
    match state.ai_bridge.search_suno_library(
        query.q.as_deref(),
        query.genre.as_deref(),
        query.tempo_min,
        query.tempo_max,
    ) {
        Ok(tracks) => {
            let count = tracks.len();
            Ok(Json(TracksResponse { tracks, count }))
        }
        Err(_) => Err(StatusCode::INTERNAL_SERVER_ERROR),
    }
}

/// Import track handler
async fn import_track(
    State(_state): State<Arc<ApiState>>,
    Json(request): Json<ImportRequest>,
) -> Json<ImportResponse> {
    // TODO: Implement actual import to project
    Json(ImportResponse {
        success: true,
        message: format!(
            "Track {} imported to track {}, scene {}",
            request.track_id, request.target_track, request.target_scene
        ),
    })
}

/// Health check handler
async fn health_check() -> &'static str {
    "OK"
}

/// Create the API router
pub fn create_router(state: Arc<ApiState>) -> Router {
    let cors = CorsLayer::new()
        .allow_origin(Any)
        .allow_methods(Any)
        .allow_headers(Any);

    Router::new()
        .route("/health", get(health_check))
        .route("/api/tracks", get(get_tracks))
        .route("/api/search", get(search_tracks))
        .route("/api/import", post(import_track))
        .layer(cors)
        .with_state(state)
}

/// Start the API server
pub async fn start_server(port: u16) -> Result<(), Box<dyn std::error::Error>> {
    let state = Arc::new(ApiState::new());
    let app = create_router_with_all_endpoints(state);

    let listener = tokio::net::TcpListener::bind(format!("127.0.0.1:{}", port)).await?;
    println!("API server listening on http://127.0.0.1:{}", port);

    axum::serve(listener, app).await?;
    Ok(())
}

// ============== Engine Endpoints ==============

/// Engine status response
#[derive(Debug, Serialize)]
pub struct EngineStatusResponse {
    pub initialized: bool,
    pub sample_rate: u32,
    pub buffer_size: u32,
}

/// Engine init request
#[derive(Debug, Deserialize)]
pub struct EngineInitRequest {
    pub sample_rate: Option<u32>,
    pub buffer_size: Option<u32>,
}

/// Engine init handler
async fn engine_init(Json(_req): Json<EngineInitRequest>) -> Result<Json<serde_json::Value>, StatusCode> {
    // TODO: Initialize actual engine through FFI bridge
    Ok(Json(serde_json::json!({
        "success": true,
        "message": "Engine initialized",
        "sample_rate": _req.sample_rate.unwrap_or(44100),
        "buffer_size": _req.buffer_size.unwrap_or(512),
    })))
}

/// Engine shutdown handler
async fn engine_shutdown() -> Result<Json<serde_json::Value>, StatusCode> {
    // TODO: Shutdown actual engine
    Ok(Json(serde_json::json!({
        "success": true,
        "message": "Engine shutdown",
    })))
}

/// Engine status handler
async fn engine_status() -> Result<Json<EngineStatusResponse>, StatusCode> {
    // TODO: Get actual engine status
    Ok(Json(EngineStatusResponse {
        initialized: true,
        sample_rate: 44100,
        buffer_size: 512,
    }))
}

// ============== Transport Endpoints ==============

/// Transport state response
#[derive(Debug, Serialize)]
pub struct TransportStateResponse {
    pub state: String, // "playing", "paused", "stopped"
    pub position_seconds: f64,
    pub bpm: f32,
}

/// Transport play handler
async fn transport_play() -> Result<Json<serde_json::Value>, StatusCode> {
    // TODO: Call actual transport play through FFI bridge
    Ok(Json(serde_json::json!({
        "success": true,
        "state": "playing",
    })))
}

/// Transport pause handler
async fn transport_pause() -> Result<Json<serde_json::Value>, StatusCode> {
    Ok(Json(serde_json::json!({
        "success": true,
        "state": "paused",
    })))
}

/// Transport stop handler
async fn transport_stop() -> Result<Json<serde_json::Value>, StatusCode> {
    Ok(Json(serde_json::json!({
        "success": true,
        "state": "stopped",
    })))
}

/// Transport seek request
#[derive(Debug, Deserialize)]
pub struct TransportSeekRequest {
    pub position_seconds: f64,
}

/// Transport seek handler
async fn transport_seek(Json(req): Json<TransportSeekRequest>) -> Result<Json<serde_json::Value>, StatusCode> {
    Ok(Json(serde_json::json!({
        "success": true,
        "position_seconds": req.position_seconds,
    })))
}

/// Transport status handler
async fn transport_status() -> Result<Json<TransportStateResponse>, StatusCode> {
    Ok(Json(TransportStateResponse {
        state: "stopped".to_string(),
        position_seconds: 0.0,
        bpm: 120.0,
    }))
}

// ============== ACE-Step Pattern Generation Endpoints ==============

/// Pattern generation request
#[derive(Debug, Deserialize)]
pub struct GeneratePatternRequest {
    pub bpm: f32,
    pub duration_bars: u32,
    pub style: String,
    pub key: Option<String>,
}

/// Pattern note
#[derive(Debug, Serialize)]
pub struct PatternNote {
    pub pitch: u8,
    pub velocity: u8,
    pub start_beat: f32,
    pub duration_beats: f32,
}

/// Pattern generation response
#[derive(Debug, Serialize)]
pub struct PatternResponse {
    pub success: bool,
    pub notes: Vec<PatternNote>,
    pub bpm: f32,
    pub key: String,
    pub bars: u32,
    pub error: Option<String>,
}

/// Generate pattern handler
async fn generate_pattern(Json(req): Json<GeneratePatternRequest>) -> Result<Json<PatternResponse>, StatusCode> {
    // TODO: Integrate with actual ACE-Step pattern generator
    // For now, return mock pattern
    let notes = vec![
        PatternNote { pitch: 60, velocity: 100, start_beat: 0.0, duration_beats: 0.5 },
        PatternNote { pitch: 64, velocity: 100, start_beat: 1.0, duration_beats: 0.5 },
        PatternNote { pitch: 67, velocity: 100, start_beat: 2.0, duration_beats: 0.5 },
        PatternNote { pitch: 72, velocity: 100, start_beat: 3.0, duration_beats: 1.0 },
    ];
    
    Ok(Json(PatternResponse {
        success: true,
        notes,
        bpm: req.bpm,
        key: req.key.unwrap_or_else(|| "C major".to_string()),
        bars: req.duration_bars,
        error: None,
    }))
}

// ============== Stem Extractor Endpoints ==============

/// Stem extraction request
#[derive(Debug, Deserialize)]
pub struct StemExtractRequest {
    pub input_path: String,
    pub output_dir: String,
    pub model: Option<String>, // "htdemucs", "mdx", etc.
}

/// Stem extraction response
#[derive(Debug, Serialize)]
pub struct StemExtractResponse {
    pub job_id: String,
    pub status: String, // "processing", "complete", "failed"
    pub stems: Option<Vec<StemFile>>,
    pub error: Option<String>,
}

/// Stem file info
#[derive(Debug, Serialize)]
pub struct StemFile {
    pub stem_type: String, // "drums", "bass", "vocals", "other"
    pub file_path: String,
}

/// Start stem extraction handler
async fn stem_extract(Json(_req): Json<StemExtractRequest>) -> Result<Json<StemExtractResponse>, StatusCode> {
    // TODO: Integrate with actual stem separation module
    let job_id = format!("stem_{}", std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_secs());
    
    Ok(Json(StemExtractResponse {
        job_id,
        status: "processing".to_string(),
        stems: None,
        error: None,
    }))
}

/// Stem extraction status request
#[derive(Debug, Deserialize)]
pub struct StemStatusRequest {
    pub job_id: String,
}

/// Get stem extraction status handler
async fn stem_status(axum::extract::Path(job_id): axum::extract::Path<String>) -> Result<Json<StemExtractResponse>, StatusCode> {
    // TODO: Check actual job status from stem separation module
    Ok(Json(StemExtractResponse {
        job_id,
        status: "processing".to_string(),
        stems: None,
        error: None,
    }))
}

/// Update the router to include all new endpoints
pub fn create_router_with_all_endpoints(state: Arc<ApiState>) -> Router {
    let cors = CorsLayer::new()
        .allow_origin(Any)
        .allow_methods(Any)
        .allow_headers(Any);

    Router::new()
        // Health
        .route("/health", get(health_check))
        // Engine
        .route("/api/engine/init", post(engine_init))
        .route("/api/engine/shutdown", post(engine_shutdown))
        .route("/api/engine/status", get(engine_status))
        // Transport
        .route("/api/transport/play", post(transport_play))
        .route("/api/transport/pause", post(transport_pause))
        .route("/api/transport/stop", post(transport_stop))
        .route("/api/transport/seek", post(transport_seek))
        .route("/api/transport/status", get(transport_status))
        // ACE-Step Pattern Generation
        .route("/api/ai/generate-pattern", post(generate_pattern))
        // Stem Extractor
        .route("/api/stem-extractor/extract", post(stem_extract))
        .route("/api/stem-extractor/status/:job_id", get(stem_status))
        // Suno Library
        .route("/api/tracks", get(get_tracks))
        .route("/api/search", get(search_tracks))
        .route("/api/import", post(import_track))
        .layer(cors)
        .with_state(state)
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::body::Body;
    use axum::http::{Request, Response, StatusCode};
    use tower::util::ServiceExt;

    fn create_test_app() -> Router {
        let state = Arc::new(ApiState::new());
        create_router(state)
    }

    #[tokio::test]
    async fn test_health_check() {
        let app = create_test_app();

        let response: Response<Body> = app
            .oneshot(Request::builder().uri("/health").body(Body::empty()).unwrap())
            .await
            .unwrap();

        assert_eq!(response.status(), StatusCode::OK);
    }

    #[tokio::test]
    async fn test_get_tracks() {
        let app = create_test_app();

        let response: Response<Body> = app
            .oneshot(Request::builder().uri("/api/tracks").body(Body::empty()).unwrap())
            .await
            .unwrap();

        assert_eq!(response.status(), StatusCode::OK);
    }

    #[tokio::test]
    async fn test_search_tracks() {
        let app = create_test_app();

        let response: Response<Body> = app
            .oneshot(
                Request::builder()
                    .uri("/api/search?q=test&genre=electronic&tempo_min=120&tempo_max=130")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(response.status(), StatusCode::OK);
    }

    #[tokio::test]
    async fn test_import_track() {
        let app = create_test_app();

        let request_body = serde_json::json!({
            "track_id": "test_001",
            "target_track": 0,
            "target_scene": 1
        });

        let response: Response<Body> = app
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/api/import")
                    .header("content-type", "application/json")
                    .body(Body::from(request_body.to_string()))
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(response.status(), StatusCode::OK);
    }
}
