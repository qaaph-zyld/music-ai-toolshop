//! OpenDAW Engine Server
//!
//! Standalone HTTP API server for the OpenDAW audio engine.
//! Provides REST endpoints for UI communication without FFI complexity.

use daw_engine::{start_server, init_from_env};

#[cfg(feature = "tracy")]
use tracy_client;

#[tokio::main]
async fn main() {
    // Initialize Tracy client if feature enabled and env var set
    #[cfg(feature = "tracy")]
    let _tracy_client = if init_from_env() {
        Some(tracy_client::Client::start())
    } else {
        None
    };

    println!("╔══════════════════════════════════════════════════════════════╗");
    println!("║           OpenDAW Engine Server (Axum REST API)              ║");
    println!("╠══════════════════════════════════════════════════════════════╣");
    #[cfg(feature = "tracy")]
    {
        if init_from_env() {
            println!("║ Tracy Profiler: ENABLED (OPENDAW_TRACY=1)                    ║");
        } else {
            println!("║ Tracy Profiler: available (set OPENDAW_TRACY=1 to enable)  ║");
        }
    }
    #[cfg(not(feature = "tracy"))]
    println!("║ Tracy Profiler: disabled (zero overhead)                     ║");
    println!("║ Endpoints:                                                   ║");
    println!("║   GET  /health                    - Health check             ║");
    println!("║   POST /api/engine/init           - Initialize engine        ║");
    println!("║   POST /api/engine/shutdown       - Shutdown engine          ║");
    println!("║   GET  /api/engine/status         - Get engine status        ║");
    println!("║   POST /api/transport/play        - Start playback           ║");
    println!("║   POST /api/transport/pause        - Pause playback           ║");
    println!("║   POST /api/transport/stop        - Stop playback            ║");
    println!("║   POST /api/transport/seek         - Seek to position          ║");
    println!("║   GET  /api/transport/status       - Get transport state       ║");
    println!("║   POST /api/ai/generate-pattern    - Generate MIDI pattern     ║");
    println!("║   POST /api/stem-extractor/extract - Start stem extraction     ║");
    println!("║   GET  /api/stem-extractor/status/:id - Check extraction status ║");
    println!("║   GET  /api/tracks                - Get Suno library tracks  ║");
    println!("║   GET  /api/search?q=...          - Search tracks             ║");
    println!("║   POST /api/import                - Import track             ║");
    println!("╚══════════════════════════════════════════════════════════════╝");
    println!();
    
    let port = std::env::var("OPENDAW_PORT")
        .ok()
        .and_then(|p| p.parse().ok())
        .unwrap_or(3000);
    
    println!("Starting server on port {}...", port);
    
    if let Err(e) = start_server(port).await {
        eprintln!("Server error: {}", e);
        std::process::exit(1);
    }
}
