//! OpenDAW Engine Server
//!
//! Standalone HTTP API server for the OpenDAW audio engine.
//! Provides REST endpoints for UI communication without FFI complexity.

use daw_engine::start_server;

#[tokio::main]
async fn main() {
    println!("╔══════════════════════════════════════════════════════════════╗");
    println!("║           OpenDAW Engine Server (Axum REST API)              ║");
    println!("╠══════════════════════════════════════════════════════════════╣");
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
