"""
Production Analyzer - Batch Analysis Module

Analyzes multiple audio variants to detect and reverse-engineer
mix/mastering processing chains using spectral fingerprinting.
"""

from __future__ import annotations
import json
import sqlite3
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import numpy as np
from collections import defaultdict


@dataclass
class AudioFingerprint:
    """Audio fingerprint with spectral features."""
    file_path: str
    track_name: str
    variant_type: str
    centroid: float
    rolloff: float
    flux: float
    flatness: float
    crest_factor: float
    rms_db: float
    peak_db: float
    lufs_estimate: float
    zcr: float
    bandwidth: float
    sample_rate: int
    duration_sec: float
    parent_id: Optional[int] = None


@dataclass
class ProcessingRecipe:
    """Detected processing chain recipe."""
    eq_changes: List[Tuple[float, float]]  # (frequency_hz, gain_db)
    compression_db: float
    compression_confidence: float
    reverb_rt60: float
    reverb_confidence: float
    stereo_width_ratio: float
    limiting_detected: bool
    loudness_change_db: float
    spectral_shift_hz: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "eq_changes": self.eq_changes,
            "compression_db": self.compression_db,
            "compression_confidence": self.compression_confidence,
            "reverb_rt60": self.reverb_rt60,
            "reverb_confidence": self.reverb_confidence,
            "stereo_width_ratio": self.stereo_width_ratio,
            "limiting_detected": self.limiting_detected,
            "loudness_change_db": self.loudness_change_db,
            "spectral_shift_hz": self.spectral_shift_hz,
        }


class RustBridge:
    """Bridge to Rust audio analysis engine via CLI."""
    
    def __init__(self, engine_path: Optional[str] = None):
        self.engine_path = engine_path or self._find_engine()
    
    def _find_engine(self) -> str:
        """Find the Rust engine binary."""
        # Look for cargo-built binary
        possible_paths = [
            "daw-engine/target/debug/daw-engine-cli.exe",
            "daw-engine/target/release/daw-engine-cli.exe",
            "../daw-engine/target/debug/daw-engine-cli",
            "../daw-engine/target/release/daw-engine-cli",
        ]
        for path in possible_paths:
            if Path(path).exists():
                return path
        return "daw-engine"  # Default to PATH
    
    def analyze_file(self, file_path: str) -> Optional[AudioFingerprint]:
        """Analyze single audio file using Rust engine."""
        # For now, use a placeholder - real implementation would call Rust CLI
        # This will be implemented when CLI is built
        return None
    
    def compare_files(self, dry_path: str, processed_path: str) -> Optional[ProcessingRecipe]:
        """Compare two files and detect processing."""
        # Placeholder - real implementation would call Rust CLI
        return None


class BatchAnalyzer:
    """Batch analyze audio files for production reverse engineering."""
    
    def __init__(self, db_path: str = "production_analysis.db"):
        self.db_path = db_path
        self.bridge = RustBridge()
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS fingerprints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE,
                track_name TEXT,
                variant_type TEXT,
                centroid REAL,
                rolloff REAL,
                flux REAL,
                flatness REAL,
                crest_factor REAL,
                rms_db REAL,
                peak_db REAL,
                lufs_estimate REAL,
                zcr REAL,
                bandwidth REAL,
                sample_rate INTEGER,
                duration_sec REAL,
                parent_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS processing_chains (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER,
                target_id INTEGER,
                recipe_json TEXT,
                similarity_score REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
    
    def analyze_directory(
        self, 
        directory: str, 
        pattern: str = "*.wav",
        recursive: bool = True
    ) -> List[AudioFingerprint]:
        """Analyze all matching files in a directory."""
        dir_path = Path(directory)
        if not dir_path.exists():
            raise ValueError(f"Directory not found: {directory}")
        
        # Find all matching files
        if recursive:
            files = list(dir_path.rglob(pattern))
        else:
            files = list(dir_path.glob(pattern))
        
        fingerprints = []
        for file_path in files:
            fp = self._analyze_single_file(str(file_path))
            if fp:
                fingerprints.append(fp)
                self._store_fingerprint(fp)
        
        return fingerprints
    
    def _analyze_single_file(self, file_path: str) -> Optional[AudioFingerprint]:
        """Analyze a single audio file."""
        try:
            import librosa
            
            # Load audio
            y, sr = librosa.load(file_path, sr=None, mono=True)
            
            # Extract features
            spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)
            spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)
            spectral_flux = librosa.onset.onset_strength(y=y, sr=sr)
            
            # Compute statistics
            centroid = float(np.mean(spectral_centroids))
            rolloff = float(np.mean(spectral_rolloff))
            flux = float(np.mean(spectral_flux))
            
            # Spectral flatness
            flatness_data = librosa.feature.spectral_flatness(y=y)
            flatness = float(np.mean(flatness))
            
            # Time-domain features
            rms = float(np.sqrt(np.mean(y**2)))
            peak = float(np.max(np.abs(y)))
            
            # Zero crossing rate
            zcr = float(np.mean(librosa.feature.zero_crossing_rate(y)))
            
            # Bandwidth
            bandwidth_data = librosa.feature.spectral_bandwidth(y=y, sr=sr)
            bandwidth = float(np.mean(bandwidth_data))
            
            # Convert to dB
            rms_db = 20 * np.log10(rms + 1e-10)
            peak_db = 20 * np.log10(peak + 1e-10)
            crest_factor = peak_db - rms_db
            
            # Simple LUFS estimate
            lufs_estimate = rms_db - 14.0
            
            # Extract track name from path
            path = Path(file_path)
            track_name = path.stem
            
            # Detect variant type from filename
            variant_type = self._detect_variant_type(track_name)
            
            return AudioFingerprint(
                file_path=file_path,
                track_name=track_name,
                variant_type=variant_type,
                centroid=centroid,
                rolloff=rolloff,
                flux=flux,
                flatness=flatness,
                crest_factor=crest_factor,
                rms_db=rms_db,
                peak_db=peak_db,
                lufs_estimate=lufs_estimate,
                zcr=zcr,
                bandwidth=bandwidth,
                sample_rate=sr,
                duration_sec=len(y) / sr,
            )
            
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
            return None
    
    def _detect_variant_type(self, filename: str) -> str:
        """Detect variant type from filename."""
        lower = filename.lower()
        
        if any(x in lower for x in ['master', 'final']):
            return 'master'
        elif any(x in lower for x in ['mix', 'mixdown']):
            return 'mix'
        elif any(x in lower for x in ['stem', 'stems']):
            return 'stem'
        elif any(x in lower for x in ['vocal', 'vocals']):
            return 'vocal'
        elif any(x in lower for x in ['remix', 'edit']):
            return 'remix'
        elif any(x in lower for x in ['original', 'demo', 'raw']):
            return 'original'
        else:
            return 'unknown'
    
    def _store_fingerprint(self, fp: AudioFingerprint):
        """Store fingerprint in database."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT OR REPLACE INTO fingerprints (
                file_path, track_name, variant_type,
                centroid, rolloff, flux, flatness, crest_factor,
                rms_db, peak_db, lufs_estimate, zcr, bandwidth,
                sample_rate, duration_sec
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            fp.file_path, fp.track_name, fp.variant_type,
            fp.centroid, fp.rolloff, fp.flux, fp.flatness, fp.crest_factor,
            fp.rms_db, fp.peak_db, fp.lufs_estimate, fp.zcr, fp.bandwidth,
            fp.sample_rate, fp.duration_sec
        ))
        conn.commit()
        conn.close()
    
    def find_similar_tracks(
        self, 
        track_name: str, 
        threshold: float = 0.85
    ) -> List[Tuple[AudioFingerprint, float]]:
        """Find similar tracks using cosine similarity."""
        conn = sqlite3.connect(self.db_path)
        
        # Get reference track
        cursor = conn.execute(
            "SELECT * FROM fingerprints WHERE track_name = ?",
            (track_name,)
        )
        reference = cursor.fetchone()
        
        if not reference:
            conn.close()
            return []
        
        # Get all other tracks
        cursor = conn.execute(
            "SELECT * FROM fingerprints WHERE track_name != ?",
            (track_name,)
        )
        candidates = cursor.fetchall()
        
        conn.close()
        
        # Compute similarity for each
        results = []
        ref_features = np.array(reference[4:13])  # feature columns
        
        for row in candidates:
            cand_features = np.array(row[4:13])
            similarity = self._cosine_similarity(ref_features, cand_features)
            
            if similarity >= threshold:
                fp = AudioFingerprint(
                    file_path=row[1],
                    track_name=row[2],
                    variant_type=row[3],
                    centroid=row[4],
                    rolloff=row[5],
                    flux=row[6],
                    flatness=row[7],
                    crest_factor=row[8],
                    rms_db=row[9],
                    peak_db=row[10],
                    lufs_estimate=row[11],
                    zcr=row[12],
                    bandwidth=row[13],
                    sample_rate=row[14],
                    duration_sec=row[15],
                )
                results.append((fp, similarity))
        
        # Sort by similarity
        results.sort(key=lambda x: x[1], reverse=True)
        return results
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return float(np.dot(a, b) / (norm_a * norm_b))
    
    def cluster_by_processing(self) -> Dict[str, List[AudioFingerprint]]:
        """Cluster tracks by detected processing chains."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT * FROM fingerprints")
        rows = cursor.fetchall()
        conn.close()
        
        # Simple clustering by variant type
        clusters = defaultdict(list)
        
        for row in rows:
            fp = AudioFingerprint(
                file_path=row[1],
                track_name=row[2],
                variant_type=row[3],
                centroid=row[4],
                rolloff=row[5],
                flux=row[6],
                flatness=row[7],
                crest_factor=row[8],
                rms_db=row[9],
                peak_db=row[10],
                lufs_estimate=row[11],
                zcr=row[12],
                bandwidth=row[13],
                sample_rate=row[14],
                duration_sec=row[15],
            )
            clusters[fp.variant_type].append(fp)
        
        return dict(clusters)
    
    def generate_report(
        self, 
        track_name: str,
        output_path: Optional[str] = None
    ) -> str:
        """Generate production analysis report for a track."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT * FROM fingerprints WHERE track_name = ? ORDER BY created_at",
            (track_name,)
        )
        variants = cursor.fetchall()
        conn.close()
        
        if not variants:
            return f"No data found for track: {track_name}"
        
        report = [f"# Production Analysis Report: {track_name}", ""]
        report.append(f"## Variants Found: {len(variants)}")
        report.append("")
        
        for row in variants:
            report.append(f"### {row[3]}: {row[2]}")
            report.append(f"- Duration: {row[15]:.2f}s")
            report.append(f"- Loudness: {row[11]:.1f} LUFS estimate")
            report.append(f"- Crest Factor: {row[8]:.1f} dB")
            report.append(f"- Spectral Centroid: {row[4]:.0f} Hz")
            report.append("")
        
        # Find similar tracks
        similar = self.find_similar_tracks(track_name, threshold=0.8)
        if similar:
            report.append("## Similar Tracks")
            report.append("")
            for fp, score in similar[:5]:
                report.append(f"- {fp.track_name} ({fp.variant_type}): {score:.2%} similarity")
            report.append("")
        
        report_text = "\n".join(report)
        
        if output_path:
            with open(output_path, 'w') as f:
                f.write(report_text)
        
        return report_text
    
    def export_to_json(self, output_path: str):
        """Export all fingerprints to JSON."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT * FROM fingerprints")
        rows = cursor.fetchall()
        conn.close()
        
        data = []
        for row in rows:
            data.append({
                "id": row[0],
                "file_path": row[1],
                "track_name": row[2],
                "variant_type": row[3],
                "centroid": row[4],
                "rolloff": row[5],
                "flux": row[6],
                "flatness": row[7],
                "crest_factor": row[8],
                "rms_db": row[9],
                "peak_db": row[10],
                "lufs_estimate": row[11],
                "zcr": row[12],
                "bandwidth": row[13],
                "sample_rate": row[14],
                "duration_sec": row[15],
            })
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Exported {len(data)} fingerprints to {output_path}")


def main():
    """CLI entry point for batch analysis."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Batch audio analysis for production reverse engineering")
    parser.add_argument("command", choices=["analyze", "cluster", "report", "export"])
    parser.add_argument("--dir", "-d", help="Directory to analyze")
    parser.add_argument("--track", "-t", help="Track name for report")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--pattern", "-p", default="*.wav", help="File pattern")
    
    args = parser.parse_args()
    
    analyzer = BatchAnalyzer()
    
    if args.command == "analyze":
        if not args.dir:
            print("Error: --dir required for analyze command")
            return 1
        
        fingerprints = analyzer.analyze_directory(args.dir, pattern=args.pattern)
        print(f"Analyzed {len(fingerprints)} files")
        
    elif args.command == "cluster":
        clusters = analyzer.cluster_by_processing()
        for variant_type, tracks in clusters.items():
            print(f"\n{variant_type.upper()}: {len(tracks)} tracks")
            for fp in tracks:
                print(f"  - {fp.track_name}")
                
    elif args.command == "report":
        if not args.track:
            print("Error: --track required for report command")
            return 1
        
        report = analyzer.generate_report(args.track, args.output)
        print(report)
        
    elif args.command == "export":
        if not args.output:
            args.output = "fingerprints.json"
        analyzer.export_to_json(args.output)
    
    return 0


if __name__ == "__main__":
    exit(main())
