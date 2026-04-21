#!/usr/bin/env python3
"""Create test database and data for Suno Library API Server

This script creates:
1. SQLite database (suno_tracks.db) with tracks table
2. 10 sample tracks with varied genres and tempos
"""

import sqlite3
import os
from pathlib import Path


def create_database():
    """Create SQLite database with tracks table."""
    db_path = Path(__file__).parent / "suno_tracks.db"
    
    # Remove existing database if present
    if db_path.exists():
        db_path.unlink()
        print(f"Removed existing database: {db_path}")
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Create tracks table
    cursor.execute('''
        CREATE TABLE tracks (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            artist TEXT,
            genre TEXT,
            tempo INTEGER,
            key TEXT,
            audio_path TEXT
        )
    ''')
    
    print("Created tracks table")
    
    # Sample tracks data (audio_path is just filename, api_server adds audio/ prefix)
    tracks = [
        ("track_001", "Neon Dreams", "Suno AI", "electronic", 128, "Cm", "track_001.mp3"),
        ("track_002", "Acoustic Morning", "Suno AI", "acoustic", 90, "G", "track_002.mp3"),
        ("track_003", "Drum Loop A", "Suno AI", "drums", 140, "-", "track_003.mp3"),
        ("track_004", "Deep Bass", "Suno AI", "electronic", 128, "Cm", "track_004.mp3"),
        ("track_005", "Ambient Pad", "Suno AI", "ambient", 110, "F", "track_005.mp3"),
        ("track_006", "Pop Melody", "Suno AI", "pop", 120, "C", "track_006.mp3"),
        ("track_007", "Rock Riff", "Suno AI", "rock", 135, "E", "track_007.mp3"),
        ("track_008", "Jazz Chords", "Suno AI", "jazz", 95, "Bb", "track_008.mp3"),
        ("track_009", "Hip Hop Beat", "Suno AI", "hiphop", 88, "G", "track_009.mp3"),
        ("track_010", "Techno Pulse", "Suno AI", "techno", 130, "Am", "track_010.mp3"),
    ]
    
    cursor.executemany('''
        INSERT INTO tracks (id, title, artist, genre, tempo, key, audio_path)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', tracks)
    
    conn.commit()
    conn.close()
    
    print(f"Inserted {len(tracks)} sample tracks into database")
    print(f"Database created: {db_path}")
    
    return db_path


def verify_database():
    """Verify database contents."""
    db_path = Path(__file__).parent / "suno_tracks.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM tracks")
    count = cursor.fetchone()[0]
    print(f"\nVerification: {count} tracks in database")
    
    cursor.execute("SELECT DISTINCT genre FROM tracks")
    genres = [row[0] for row in cursor.fetchall()]
    print(f"Genres: {', '.join(genres)}")
    
    cursor.execute("SELECT MIN(tempo), MAX(tempo) FROM tracks")
    min_tempo, max_tempo = cursor.fetchone()
    print(f"Tempo range: {min_tempo} - {max_tempo} BPM")
    
    conn.close()


if __name__ == "__main__":
    print("=" * 50)
    print("Suno Library Test Database Creator")
    print("=" * 50)
    
    create_database()
    verify_database()
    
    print("\n✅ Database creation complete!")
    print("\nNext step: Generate test audio files with generate_audio.py")
