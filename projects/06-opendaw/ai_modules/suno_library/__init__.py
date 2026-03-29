"""Suno Library Browser for OpenDAW

Integration with Suno music library for sample/loop management.
"""

from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import json


@dataclass
class SunoTrack:
    """Suno track metadata"""
    id: str
    title: str
    artist: str
    genre: str
    tempo: int
    key: str
    tags: List[str]
    audio_path: Path
    lyrics: Optional[str] = None


class SunoLibrary:
    """Browser for Suno music library"""
    
    def __init__(self, library_path: Optional[Path] = None):
        if library_path is None:
            # Default to the 01-suno-library project
            self.library_path = Path("d:/Project/music-ai-toolshop/projects/01-suno-library")
        else:
            self.library_path = library_path
        
        self._cache: List[SunoTrack] = []
        self._load_cache()
    
    def _load_cache(self):
        """Load track metadata from library"""
        # TODO: Scan library directory and load metadata
        # For now, create stub entries
        self._cache = [
            SunoTrack(
                id="demo_001",
                title="Demo Track 1",
                artist="AI",
                genre="electronic",
                tempo=128,
                key="C",
                tags=["upbeat", "energetic"],
                audio_path=self.library_path / "demo_001.mp3"
            )
        ]
    
    def search(
        self,
        query: Optional[str] = None,
        genre: Optional[str] = None,
        tempo_range: Optional[Tuple[int, int]] = None,
        tags: Optional[List[str]] = None
    ) -> List[SunoTrack]:
        """Search Suno library
        
        Args:
            query: Text search query
            genre: Filter by genre
            tempo_range: (min, max) BPM
            tags: Filter by tags
            
        Returns:
            List of matching tracks
        """
        results = self._cache
        
        if query:
            query_lower = query.lower()
            results = [t for t in results 
                      if query_lower in t.title.lower() 
                      or query_lower in t.artist.lower()]
        
        if genre:
            results = [t for t in results if t.genre == genre]
        
        if tempo_range:
            min_tempo, max_tempo = tempo_range
            results = [t for t in results if min_tempo <= t.tempo <= max_tempo]
        
        if tags:
            results = [t for t in results 
                      if any(tag in t.tags for tag in tags)]
        
        return results
    
    def get_audio_path(self, track_id: str) -> Optional[Path]:
        """Resolve track ID to audio file path"""
        for track in self._cache:
            if track.id == track_id:
                return track.audio_path
        return None
    
    def preview(self, track_id: str, duration_seconds: float = 10.0) -> Optional[bytes]:
        """Get preview audio data for track
        
        Args:
            track_id: Track identifier
            duration_seconds: Length of preview
            
        Returns:
            Audio data bytes or None if track not found
        """
        track = next((t for t in self._cache if t.id == track_id), None)
        if track is None:
            return None
        
        # TODO: Load and return audio preview
        return b""
    
    def count(self) -> int:
        """Get total number of tracks in library"""
        return len(self._cache)
    
    def genres(self) -> List[str]:
        """Get list of all genres in library"""
        return list(set(t.genre for t in self._cache))
    
    def all_tags(self) -> List[str]:
        """Get list of all tags in library"""
        tags = set()
        for track in self._cache:
            tags.update(track.tags)
        return list(tags)


def search_to_daw_results(
    query: Optional[str] = None,
    genre: Optional[str] = None,
    tempo_min: Optional[int] = None,
    tempo_max: Optional[int] = None
) -> List[Dict]:
    """Convenience function for DAW integration
    
    Returns JSON-serializable list of tracks
    """
    library = SunoLibrary()
    
    tempo_range = None
    if tempo_min is not None and tempo_max is not None:
        tempo_range = (tempo_min, tempo_max)
    
    tracks = library.search(
        query=query,
        genre=genre,
        tempo_range=tempo_range
    )
    
    return [
        {
            "id": t.id,
            "title": t.title,
            "artist": t.artist,
            "genre": t.genre,
            "tempo": t.tempo,
            "key": t.key,
            "tags": t.tags,
            "audio_path": str(t.audio_path)
        }
        for t in tracks
    ]


if __name__ == "__main__":
    # Test the library browser
    library = SunoLibrary()
    print(f"Library contains {library.count()} tracks")
    
    results = library.search(genre="electronic")
    print(f"Electronic tracks: {len(results)}")
    
    for track in results:
        print(f"  - {track.title} ({track.tempo} BPM)")
