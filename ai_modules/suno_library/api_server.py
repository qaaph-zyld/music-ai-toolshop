#!/usr/bin/env python3
"""Suno Library API Server

Flask-based REST API for the Suno Library browser component.
Provides endpoints for track browsing, search, and audio streaming.

Port: 3000 (default, configurable via SUNO_API_PORT env var)
Database: SQLite (suno_tracks.db)
"""

import os
import sqlite3
from pathlib import Path
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    CORS(app)  # Enable CORS for all domains

    # Database path configuration
    db_path = Path(__file__).parent / "suno_tracks.db"
    audio_dir = Path(__file__).parent / "audio"

    def get_db_connection():
        """Create a database connection with row factory."""
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        return conn

    @app.route('/api/health', methods=['GET'])
    def health_check():
        """Health check endpoint."""
        return jsonify({'status': 'ok', 'service': 'suno-library-api'})

    @app.route('/api/tracks', methods=['GET'])
    def list_tracks():
        """List all tracks with optional pagination.
        
        Query params:
            page: Page number (default: 1)
            per_page: Items per page (default: 50, max: 100)
        """
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        per_page = min(per_page, 100)  # Cap at 100

        offset = (page - 1) * per_page

        conn = get_db_connection()
        cursor = conn.cursor()

        # Get total count
        cursor.execute('SELECT COUNT(*) FROM tracks')
        total = cursor.fetchone()[0]

        # Get tracks
        cursor.execute('''
            SELECT id, title, artist, genre, tempo, key, audio_path
            FROM tracks
            LIMIT ? OFFSET ?
        ''', (per_page, offset))

        tracks = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return jsonify({
            'tracks': tracks,
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page
        })

    @app.route('/api/search', methods=['GET'])
    def search_tracks():
        """Search tracks by query, genre, tempo range.
        
        Query params:
            q: Search query for title/artist
            genre: Filter by genre
            tempo_min: Minimum tempo (BPM)
            tempo_max: Maximum tempo (BPM)
        """
        query = request.args.get('q', '').strip()
        genre = request.args.get('genre', '').strip()
        tempo_min = request.args.get('tempo_min', type=int)
        tempo_max = request.args.get('tempo_max', type=int)

        conn = get_db_connection()
        cursor = conn.cursor()

        sql = '''SELECT id, title, artist, genre, tempo, key, audio_path 
                 FROM tracks WHERE 1=1'''
        params = []

        if query:
            sql += ' AND (title LIKE ? OR artist LIKE ?)'
            params.extend([f'%{query}%', f'%{query}%'])

        if genre:
            sql += ' AND genre LIKE ?'
            params.append(f'%{genre}%')

        if tempo_min is not None:
            sql += ' AND tempo >= ?'
            params.append(tempo_min)

        if tempo_max is not None:
            sql += ' AND tempo <= ?'
            params.append(tempo_max)

        sql += ' ORDER BY title LIMIT 100'

        cursor.execute(sql, params)
        tracks = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return jsonify({'tracks': tracks, 'count': len(tracks)})

    @app.route('/api/tracks/<track_id>', methods=['GET'])
    def get_track(track_id):
        """Get a single track by ID."""
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, title, artist, genre, tempo, key, audio_path
            FROM tracks WHERE id = ?
        ''', (track_id,))

        row = cursor.fetchone()
        conn.close()

        if row is None:
            return jsonify({'error': 'Track not found'}), 404

        return jsonify(dict(row))

    @app.route('/api/tracks/<track_id>/audio', methods=['GET'])
    def stream_audio(track_id):
        """Stream audio file for a track."""
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT audio_path FROM tracks WHERE id = ?', (track_id,))
        row = cursor.fetchone()
        conn.close()

        if row is None:
            return jsonify({'error': 'Track not found'}), 404

        audio_path = Path(row['audio_path'])
        if not audio_path.is_absolute():
            audio_path = audio_dir / audio_path

        if not audio_path.exists():
            return jsonify({'error': 'Audio file not found'}), 404

        return send_file(
            audio_path,
            mimetype='audio/mpeg',
            as_attachment=False
        )

    return app


if __name__ == '__main__':
    port = int(os.environ.get('SUNO_API_PORT', 3000))
    app = create_app()
    print(f"Starting Suno Library API Server on port {port}")
    print(f"Health check: http://127.0.0.1:{port}/api/health")
    app.run(host='0.0.0.0', port=port, debug=True)
