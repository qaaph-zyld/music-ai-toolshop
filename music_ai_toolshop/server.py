#!/usr/bin/env python3
"""
Music AI Toolshop — Flask backend
Single dashboard that dispatches to the six phase tools.
"""
import json
import os
import re
import shutil
import sys
import tempfile
import urllib.parse
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request, send_file

from paths import get_repo_paths

app = Flask(__name__, template_folder="templates", static_folder="static")

REPOS = get_repo_paths()
UPLOAD_DIR = Path(tempfile.gettempdir()) / "music_ai_toolshop_uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR = Path(tempfile.gettempdir()) / "music_ai_toolshop_outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_\-]", "_", name).strip("_")[:60]


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/health")
def api_health():
    return jsonify({"ok": True, "repos": {k: str(v) for k, v in REPOS.items()}})


@app.route("/api/tools")
def api_tools():
    return jsonify([
        {
            "id": "stem_extractor",
            "name": "Stem Extractor",
            "description": "Separate a mix into vocal and instrumental stems via open_DAW.",
            "inputs": [{"name": "file", "type": "file", "accept": "audio/*"}],
            "params": [
                {"name": "backend", "type": "select", "default": "roformer", "options": ["roformer", "demucs"]},
                {"name": "stem", "type": "text", "default": "vocals,instrumental", "label": "Stems (comma-separated)"},
            ],
        },
        {
            "id": "vocal_restore",
            "name": "Vocal Restore",
            "description": "Run the vocal restoration chain on a vocal stem.",
            "inputs": [{"name": "file", "type": "file", "accept": ".wav"}],
            "params": [
                {"name": "stage", "type": "select", "default": "all", "options": ["all", "deroom", "voicefixer", "apollo", "audiosr"]},
            ],
        },
        {
            "id": "clap_match",
            "name": "CLAP Reference Match",
            "description": "Find top-K nearest references for a track using CLAP embeddings.",
            "inputs": [{"name": "file", "type": "file", "accept": "audio/*"}],
            "params": [
                {"name": "k", "type": "number", "default": "5", "label": "Top K"},
                {"name": "genre", "type": "text", "default": "", "label": "Genre filter (optional)"},
            ],
        },
        {
            "id": "vocal_qc",
            "name": "Vocal QC",
            "description": "Run Whisper transcription and confidence diagnostics on a vocal stem.",
            "inputs": [{"name": "file", "type": "file", "accept": "audio/*"}],
            "params": [
                {"name": "lyric", "type": "text", "default": "", "label": "Lyric text (optional)"},
            ],
        },
        {
            "id": "neutone_preview",
            "name": "Neutone Plugin Preview",
            "description": "Real-time Neutone plugin preview (requires open_DAW desktop app).",
            "inputs": [],
            "params": [],
            "external": True,
        },
        {
            "id": "master_bus_preview",
            "name": "Master Bus Preview",
            "description": "Real-time master bus preview (requires open_DAW desktop app).",
            "inputs": [],
            "params": [],
            "external": True,
        },
    ])


@app.route("/api/upload", methods=["POST"])
def api_upload():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    f = request.files["file"]
    if f.filename == "":
        return jsonify({"error": "Empty filename"}), 400
    safe = _safe_name(f.filename)
    saved = UPLOAD_DIR / safe
    f.save(saved)
    return jsonify({"ok": True, "filename": f.filename, "safe": safe, "path": str(saved)})


@app.route("/api/download/<path:filename>")
def api_download(filename):
    fpath = OUTPUT_DIR / filename
    if not fpath.exists():
        return jsonify({"error": "File not found"}), 404
    return send_file(fpath, as_attachment=True)


@app.route("/api/run/<tool_id>")
def api_run(tool_id: str):
    """SSE endpoint: dispatches to a tool wrapper and streams progress."""
    file_path = request.args.get("path", "")
    params = {k: v for k, v in request.args.items() if k != "path"}

    if tool_id not in {"stem_extractor", "vocal_restore", "clap_match", "vocal_qc"}:
        def err():
            yield "data: [ERROR] Tool not available via web dashboard\n\n"
            yield 'event: done\ndata: {"error":"Tool not available"}\n\n'
        return Response(err(), mimetype="text/event-stream")

    if not file_path or not os.path.isfile(file_path):
        def err():
            yield "data: [ERROR] Uploaded file not found\n\n"
            yield 'event: done\ndata: {"error":"File not found"}\n\n'
        return Response(err(), mimetype="text/event-stream")

    module = __import__(f"wrappers.{tool_id}", fromlist=["run"])
    run_fn = getattr(module, "run")

    def generate():
        job_output_dir = OUTPUT_DIR / f"job_{tool_id}_{os.urandom(4).hex()}"
        job_output_dir.mkdir(parents=True, exist_ok=True)
        try:
            yield f"data: [UI] Starting {tool_id}...\n\n"
            yield f"data: [UI] Output dir: {job_output_dir}\n\n"

            def progress(line: str):
                for l in line.splitlines():
                    yield f"data: {l}\n\n"

            artifacts = run_fn(
                Path(file_path),
                job_output_dir,
                params,
                progress_callback=lambda line: progress(line),
            )

            # Collect explicit artifacts plus any files the tool left in the output dir.
            all_artifacts = list(artifacts)
            if job_output_dir.exists():
                for child in job_output_dir.iterdir():
                    if child.is_file() and child not in all_artifacts:
                        all_artifacts.append(child)

            files = []
            for artifact in all_artifacts:
                if artifact.exists():
                    fname = urllib.parse.quote(artifact.name)
                    files.append({
                        "name": artifact.name,
                        "url": f"/api/download/{fname}",
                        "size": artifact.stat().st_size,
                    })

            done_payload = json.dumps({"done": True, "files": files})
            yield f"event: done\ndata: {done_payload}\n\n"
        except Exception as exc:
            import traceback
            yield f"data: [ERROR] {str(exc)}\n\n"
            for line in traceback.format_exc().splitlines():
                yield f"data: {line}\n\n"
            yield f'event: done\ndata: {{"error":"{str(exc)}"}}\n\n'
        finally:
            # Clean up empty dirs if nothing produced
            if job_output_dir.exists() and not any(job_output_dir.iterdir()):
                shutil.rmtree(job_output_dir, ignore_errors=True)

    return Response(generate(), mimetype="text/event-stream")


@app.route("/api/launch-opendaw")
def api_launch_opendaw():
    return jsonify({"ok": False, "message": "Real-time preview tools require the open_DAW desktop app."})


if __name__ == "__main__":
    host = "0.0.0.0" if os.environ.get("FLASK_ENV") == "production" else "127.0.0.1"
    app.run(host=host, port=5055, debug=False)
