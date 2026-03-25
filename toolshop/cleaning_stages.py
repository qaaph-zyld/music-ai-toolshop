"""Audio cleaning pipeline stage implementations."""

from dataclasses import dataclass
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
import numpy as np
import soundfile as sf
import librosa


@dataclass
class StageResult:
    """Result from a pipeline stage."""

    audio: np.ndarray
    sample_rate: int
    metadata: Dict[str, Any]
    report: Dict[str, Any]


class PreprocessingStage:
    """Stage 1: Load audio and extract baseline features."""

    def __init__(self, target_sr: int = 44100, normalize: bool = True):
        self.target_sr = target_sr
        self.normalize = normalize

    def process(self, audio_path: str) -> StageResult:
        """Load audio and compute baseline features."""
        # Load audio
        audio, sr = librosa.load(audio_path, sr=self.target_sr, mono=True)

        if self.normalize:
            audio = librosa.util.normalize(audio)

        # Compute features
        duration = librosa.get_duration(y=audio, sr=sr)

        # Energy envelope (for later stages)
        hop_length = 512
        frame_length = 2048
        rms = librosa.feature.rms(
            y=audio, frame_length=frame_length, hop_length=hop_length
        )[0]

        # Spectral features
        spectral_centroid = librosa.feature.spectral_centroid(y=audio, sr=sr)[0].mean()
        spectral_bandwidth = librosa.feature.spectral_bandwidth(y=audio, sr=sr)[
            0
        ].mean()

        # Detect BPM and key
        tempo, beat_frames = librosa.beat.beat_track(y=audio, sr=sr)

        # Key detection (chromagram-based)
        chromagram = librosa.feature.chroma_stft(y=audio, sr=sr)
        key = self._detect_key(chromagram)

        metadata = {
            "duration": duration,
            "sample_rate": sr,
            "rms_envelope": rms,
            "hop_length": hop_length,
            "frame_length": frame_length,
            "spectral_centroid": float(spectral_centroid),
            "spectral_bandwidth": float(spectral_bandwidth),
            "bpm": float(tempo),
            "key": key,
            "beat_frames": beat_frames.tolist(),
        }

        report = {
            "stage": "preprocessing",
            "duration_seconds": duration,
            "sample_rate": sr,
            "bpm": float(tempo),
            "key": key,
            "status": "success",
        }

        return StageResult(audio, sr, metadata, report)

    def _detect_key(self, chromagram: np.ndarray) -> str:
        """Simple key detection from chromagram."""
        # Mean chroma values across time
        chroma_mean = chromagram.mean(axis=1)

        # Note names
        notes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

        # Find root note (highest chroma value)
        root_idx = chroma_mean.argmax()
        root_note = notes[root_idx]

        # Simple major/minor detection based on 3rd and 6th
        third_idx = (root_idx + 4) % 12  # Major 3rd
        minor_third_idx = (root_idx + 3) % 12  # Minor 3rd

        if chroma_mean[minor_third_idx] > chroma_mean[third_idx]:
            return f"{root_note} minor"
        else:
            return f"{root_note} major"


class PauseRemovalStage:
    """Stage 2: Detect and remove long pauses/silences."""

    def __init__(
        self,
        min_silence: float = 0.3,
        max_keep: float = 0.5,
        threshold_db: float = -40,
        crossfade_ms: float = 10,
    ):
        self.min_silence = min_silence
        self.max_keep = max_keep
        self.threshold_db = threshold_db
        self.crossfade_ms = crossfade_ms

    def process(self, result: StageResult) -> StageResult:
        """Remove long silences while preserving natural pauses."""
        audio = result.audio
        sr = result.sample_rate

        # Convert threshold from dB to amplitude
        threshold_amp = 10 ** (self.threshold_db / 20)

        # Detect non-silent intervals
        intervals = librosa.effects.split(
            audio,
            top_db=abs(self.threshold_db),
            frame_length=result.metadata["frame_length"],
            hop_length=result.metadata["hop_length"],
        )

        if len(intervals) == 0:
            # Entirely silent audio
            return StageResult(
                audio,
                sr,
                result.metadata,
                {
                    "stage": "pause_removal",
                    "removed_regions": [],
                    "status": "no_audio_detected",
                },
            )

        # Calculate gaps between intervals
        removed_regions = []
        processed_segments = []

        for i, (start, end) in enumerate(intervals):
            segment = audio[start:end]

            # Add crossfade at beginning (except first segment)
            if i > 0 and len(processed_segments) > 0:
                segment = self._apply_fade(segment, sr, "in", self.crossfade_ms)
                # Blend with previous segment's fade-out
                if len(processed_segments[-1]) >= self._samples_from_ms(
                    self.crossfade_ms, sr
                ):
                    processed_segments[-1] = self._apply_fade(
                        processed_segments[-1], sr, "out", self.crossfade_ms
                    )

            processed_segments.append(segment)

            # Record gap after this segment (except last)
            if i < len(intervals) - 1:
                next_start = intervals[i + 1][0]
                gap_duration = (next_start - end) / sr

                if gap_duration >= self.min_silence:
                    removed_regions.append(
                        {
                            "start": end / sr,
                            "end": next_start / sr,
                            "duration": gap_duration,
                            "kept": min(gap_duration, self.max_keep),
                        }
                    )

        # Concatenate all segments
        if processed_segments:
            cleaned_audio = np.concatenate(processed_segments)
        else:
            cleaned_audio = audio

        # Update metadata
        metadata = result.metadata.copy()
        metadata["original_duration"] = metadata["duration"]
        metadata["duration"] = len(cleaned_audio) / sr

        report = {
            "stage": "pause_removal",
            "original_duration": metadata["original_duration"],
            "new_duration": metadata["duration"],
            "time_removed": metadata["original_duration"] - metadata["duration"],
            "segments_kept": len(intervals),
            "removed_regions": removed_regions,
            "status": "success",
        }

        return StageResult(cleaned_audio, sr, metadata, report)

    def _samples_from_ms(self, ms: float, sr: int) -> int:
        """Convert milliseconds to samples."""
        return int(ms / 1000 * sr)

    def _apply_fade(
        self, audio: np.ndarray, sr: int, fade_type: str, duration_ms: float
    ) -> np.ndarray:
        """Apply fade in or out."""
        fade_samples = self._samples_from_ms(duration_ms, sr)

        if fade_samples >= len(audio):
            return audio

        faded = audio.copy()

        if fade_type == "in":
            fade_curve = np.linspace(0, 1, fade_samples)
            faded[:fade_samples] *= fade_curve
        else:  # fade out
            fade_curve = np.linspace(1, 0, fade_samples)
            faded[-fade_samples:] *= fade_curve

        return faded


class BreathDetectionStage:
    """Stage 3: Detect and attenuate breath sounds and exhales."""

    def __init__(
        self,
        method: str = "combined",
        attenuation_db: float = 15,
        frequency_range: Tuple[float, float] = (200, 2000),
        min_breath_duration: float = 0.1,
        max_breath_duration: float = 0.8,
    ):
        self.method = method
        self.attenuation_db = attenuation_db
        self.frequency_range = frequency_range
        self.min_breath_duration = min_breath_duration
        self.max_breath_duration = max_breath_duration

    def process(self, result: StageResult) -> StageResult:
        """Detect and attenuate breath sounds."""
        audio = result.audio
        sr = result.sample_rate

        # Run detection methods
        detections = []

        if self.method in ["frequency", "combined"]:
            detections.extend(self._detect_by_frequency(audio, sr))

        if self.method in ["energy", "combined"]:
            detections.extend(self._detect_by_energy(audio, sr))

        # Merge overlapping detections
        merged = self._merge_detections(detections)

        # Apply attenuation
        processed_audio = self._attenuate_regions(audio, sr, merged)

        report = {
            "stage": "breath_detection",
            "method": self.method,
            "breaths_detected": len(merged),
            "detections": [
                {
                    "start": d["start"],
                    "end": d["end"],
                    "duration": d["end"] - d["start"],
                    "confidence": d["confidence"],
                }
                for d in merged
            ],
            "attenuation_applied_db": self.attenuation_db,
            "status": "success",
        }

        return StageResult(processed_audio, sr, result.metadata, report)

    def _detect_by_frequency(self, audio: np.ndarray, sr: int) -> List[Dict]:
        """Detect breaths using spectral analysis in 200-2000Hz range."""
        # Compute STFT
        hop_length = 512
        D = librosa.stft(audio, hop_length=hop_length)
        freqs = librosa.fft_frequencies(sr=sr)

        # Focus on breath frequency range
        breath_mask = (freqs >= self.frequency_range[0]) & (
            freqs <= self.frequency_range[1]
        )
        breath_energy = np.abs(D[breath_mask, :]).mean(axis=0)

        # Normalize
        breath_energy = (breath_energy - breath_energy.min()) / (
            breath_energy.max() - breath_energy.min() + 1e-8
        )

        # Find peaks in breath energy
        from scipy.signal import find_peaks

        peaks, properties = find_peaks(
            breath_energy, height=0.3, distance=int(0.5 * sr / hop_length)
        )

        detections = []
        for peak in peaks:
            # Calculate breath region around peak
            start_frame = max(0, peak - int(0.2 * sr / hop_length))
            end_frame = min(len(breath_energy), peak + int(0.3 * sr / hop_length))

            start_time = start_frame * hop_length / sr
            end_time = end_frame * hop_length / sr
            duration = end_time - start_time

            if self.min_breath_duration <= duration <= self.max_breath_duration:
                detections.append(
                    {
                        "start": start_time,
                        "end": end_time,
                        "confidence": float(breath_energy[peak]),
                        "method": "frequency",
                    }
                )

        return detections

    def _detect_by_energy(self, audio: np.ndarray, sr: int) -> List[Dict]:
        """Detect breaths using energy envelope characteristics."""
        hop_length = 512
        frame_length = 2048

        # Compute RMS energy
        rms = librosa.feature.rms(
            y=audio, frame_length=frame_length, hop_length=hop_length
        )[0]

        # Smooth the envelope
        from scipy.ndimage import gaussian_filter1d

        rms_smooth = gaussian_filter1d(rms, sigma=3)

        # Find gentle attacks and decays (breath characteristic)
        detections = []
        threshold = rms_smooth.mean() * 0.3  # Low threshold for breaths

        i = 0
        while i < len(rms_smooth):
            if rms_smooth[i] > threshold:
                # Find start (going backwards)
                start = i
                while start > 0 and rms_smooth[start] < threshold * 0.5:
                    start -= 1

                # Find end (going forwards)
                end = i
                while end < len(rms_smooth) - 1 and rms_smooth[end] > threshold * 0.5:
                    end += 1

                start_time = start * hop_length / sr
                end_time = end * hop_length / sr
                duration = end_time - start_time

                if self.min_breath_duration <= duration <= self.max_breath_duration:
                    # Calculate confidence based on energy rise/fall pattern
                    confidence = min(1.0, rms_smooth[i] / (threshold * 2))
                    detections.append(
                        {
                            "start": start_time,
                            "end": end_time,
                            "confidence": confidence,
                            "method": "energy",
                        }
                    )

                i = end + 1
            else:
                i += 1

        return detections

    def _merge_detections(self, detections: List[Dict]) -> List[Dict]:
        """Merge overlapping detections, keeping highest confidence."""
        if not detections:
            return []

        # Sort by start time
        sorted_dets = sorted(detections, key=lambda x: x["start"])

        merged = [sorted_dets[0]]

        for det in sorted_dets[1:]:
            last = merged[-1]

            # Check for overlap
            if det["start"] <= last["end"] + 0.05:  # 50ms tolerance
                # Merge - extend end and take max confidence
                last["end"] = max(last["end"], det["end"])
                last["confidence"] = max(last["confidence"], det["confidence"])
                last["method"] = "combined"
            else:
                merged.append(det)

        # Filter by confidence threshold
        return [d for d in merged if d["confidence"] > 0.3]

    def _attenuate_regions(
        self, audio: np.ndarray, sr: int, regions: List[Dict]
    ) -> np.ndarray:
        """Apply attenuation to detected breath regions."""
        attenuation_factor = 10 ** (-self.attenuation_db / 20)
        processed = audio.copy()

        for region in regions:
            start_sample = int(region["start"] * sr)
            end_sample = int(region["end"] * sr)

            # Ensure bounds
            start_sample = max(0, start_sample)
            end_sample = min(len(processed), end_sample)

            # Apply smooth attenuation with short fade in/out
            fade_samples = int(0.01 * sr)  # 10ms fade

            region_length = end_sample - start_sample
            if region_length <= 0:
                continue

            # Create attenuation envelope
            envelope = np.ones(region_length) * attenuation_factor

            # Apply fades
            if region_length > 2 * fade_samples:
                fade_in = np.linspace(1.0, attenuation_factor, fade_samples)
                fade_out = np.linspace(attenuation_factor, 1.0, fade_samples)
                envelope[:fade_samples] = fade_in
                envelope[-fade_samples:] = fade_out

            processed[start_sample:end_sample] *= envelope

        return processed


class EventDetectionStage:
    """Stage 4: Detect and remove discrete events (coughs, clicks, pops)."""

    def __init__(
        self,
        detect_coughs: bool = True,
        detect_clicks: bool = True,
        detect_pops: bool = True,
        confidence_threshold: float = 0.7,
    ):
        self.detect_coughs = detect_coughs
        self.detect_clicks = detect_clicks
        self.detect_pops = detect_pops
        self.confidence_threshold = confidence_threshold
        self.cough_model = None  # Lazy load

    def process(self, result: StageResult) -> StageResult:
        """Detect and repair discrete audio events."""
        audio = result.audio
        sr = result.sample_rate

        events = []

        if self.detect_coughs:
            events.extend(self._detect_coughs(audio, sr))

        if self.detect_clicks:
            events.extend(self._detect_clicks(audio, sr))

        if self.detect_pops:
            events.extend(self._detect_pops(audio, sr))

        # Merge overlapping events, prioritize by severity
        merged = self._merge_events(events)

        # Repair events
        processed_audio = self._repair_events(audio, sr, merged)

        report = {
            "stage": "event_detection",
            "events_detected": len(merged),
            "coughs": len([e for e in merged if e["type"] == "cough"]),
            "clicks": len([e for e in merged if e["type"] == "click"]),
            "pops": len([e for e in merged if e["type"] == "pop"]),
            "events": [
                {
                    "type": e["type"],
                    "start": e["start"],
                    "end": e["end"],
                    "confidence": e["confidence"],
                }
                for e in merged
            ],
            "status": "success",
        }

        return StageResult(processed_audio, sr, result.metadata, report)

    def _detect_coughs(self, audio: np.ndarray, sr: int) -> List[Dict]:
        """Detect cough sounds using spectral and temporal features."""
        # Simplified cough detection using characteristics:
        # - Short duration (0.1-0.5s)
        # - High amplitude spike
        # - Broadband spectral content

        hop_length = 512
        frame_length = 2048

        # Compute features
        rms = librosa.feature.rms(
            y=audio, frame_length=frame_length, hop_length=hop_length
        )[0]
        spectral_centroid = librosa.feature.spectral_centroid(
            y=audio, sr=sr, hop_length=hop_length
        )[0]
        zero_crossing_rate = librosa.feature.zero_crossing_rate(
            y=audio, hop_length=hop_length
        )[0]

        # Find sudden amplitude spikes
        mean_rms = rms.mean()
        std_rms = rms.std()
        spike_threshold = mean_rms + 2 * std_rms

        events = []
        in_event = False
        event_start = 0

        for i in range(len(rms)):
            time = i * hop_length / sr

            if rms[i] > spike_threshold and not in_event:
                in_event = True
                event_start = time
            elif rms[i] < mean_rms and in_event:
                in_event = False
                event_end = time
                duration = event_end - event_start

                # Check if matches cough characteristics
                if 0.1 <= duration <= 0.5:
                    # High confidence for short, sharp events
                    confidence = min(1.0, rms[i - 1] / (mean_rms * 3))
                    if confidence > 0.5:
                        events.append(
                            {
                                "start": event_start,
                                "end": event_end,
                                "confidence": confidence,
                                "type": "cough",
                                "severity": "high" if confidence > 0.8 else "medium",
                            }
                        )

        return events

    def _detect_clicks(self, audio: np.ndarray, sr: int) -> List[Dict]:
        """Detect click sounds using onset detection."""
        # Use librosa onset detection
        onset_env = librosa.onset.onset_strength(y=audio, sr=sr)
        onset_frames = librosa.onset.onset_detect(
            onset_envelope=onset_env,
            sr=sr,
            wait=3,  # Minimum frames between onsets
            pre_avg=3,
            post_avg=3,
            pre_max=3,
            post_max=3,
        )

        # Filter for very sharp onsets (click characteristic)
        events = []
        onset_times = librosa.frames_to_time(onset_frames, sr=sr)

        for onset_time in onset_times:
            # Check if onset has very short duration and high spectral centroid
            frame_idx = int(onset_time * sr / 512)
            if frame_idx < len(onset_env):
                strength = onset_env[frame_idx]

                # High onset strength indicates sharp transient
                if strength > onset_env.mean() * 2:
                    events.append(
                        {
                            "start": max(0, onset_time - 0.01),
                            "end": onset_time + 0.02,
                            "confidence": min(1.0, strength / (onset_env.mean() * 4)),
                            "type": "click",
                            "severity": "medium",
                        }
                    )

        return events

    def _detect_pops(self, audio: np.ndarray, sr: int) -> List[Dict]:
        """Detect plosive pops using low-frequency energy analysis."""
        # Pops are characterized by low-frequency energy spikes
        hop_length = 512

        # Compute low-frequency energy
        D = np.abs(librosa.stft(audio, hop_length=hop_length))
        freqs = librosa.fft_frequencies(sr=sr)

        # Focus on low frequencies (pop energy is typically < 200Hz)
        low_freq_mask = freqs < 200
        low_freq_energy = D[low_freq_mask, :].mean(axis=0)

        # Find peaks in low frequency energy
        from scipy.signal import find_peaks

        peaks, properties = find_peaks(
            low_freq_energy,
            height=low_freq_energy.mean() * 2,
            distance=int(0.1 * sr / hop_length),  # Min 100ms between pops
        )

        events = []
        for peak in peaks:
            time = peak * hop_length / sr
            confidence = min(
                1.0,
                properties["peak_heights"][list(peaks).index(peak)]
                / (low_freq_energy.mean() * 4),
            )

            if confidence > 0.5:
                events.append(
                    {
                        "start": max(0, time - 0.02),
                        "end": time + 0.05,
                        "confidence": confidence,
                        "type": "pop",
                        "severity": "low",
                    }
                )

        return events

    def _merge_events(self, events: List[Dict]) -> List[Dict]:
        """Merge overlapping events, prioritizing by severity."""
        if not events:
            return []

        # Sort by start time
        sorted_events = sorted(events, key=lambda x: x["start"])

        merged = []
        for event in sorted_events:
            if not merged:
                merged.append(event)
                continue

            last = merged[-1]

            # Check overlap
            if event["start"] <= last["end"] + 0.01:  # 10ms tolerance
                # Keep the one with higher severity/confidence
                severity_order = {"high": 3, "medium": 2, "low": 1}
                if severity_order.get(event["severity"], 0) > severity_order.get(
                    last["severity"], 0
                ):
                    merged[-1] = event
                elif event["confidence"] > last["confidence"]:
                    merged[-1] = event
            else:
                merged.append(event)

        # Filter by confidence threshold
        return [e for e in merged if e["confidence"] > self.confidence_threshold]

    def _repair_events(
        self, audio: np.ndarray, sr: int, events: List[Dict]
    ) -> np.ndarray:
        """Repair detected events using spectral interpolation."""
        processed = audio.copy()

        for event in events:
            start_sample = int(event["start"] * sr)
            end_sample = int(event["end"] * sr)

            # Ensure bounds
            start_sample = max(0, start_sample)
            end_sample = min(len(processed), end_sample)

            if end_sample - start_sample < 10:
                continue

            # Simple spectral repair: use surrounding audio
            pre_samples = min(100, start_sample)
            post_samples = min(100, len(processed) - end_sample)

            if pre_samples > 10 and post_samples > 10:
                # Crossfade between pre and post regions
                pre = processed[start_sample - pre_samples : start_sample]
                post = processed[end_sample : end_sample + post_samples]

                # Create crossfade
                fade_len = min(len(pre), len(post), end_sample - start_sample)
                if fade_len > 0:
                    fade_in = np.linspace(1, 0, fade_len)
                    fade_out = np.linspace(0, 1, fade_len)

                    repair = pre[-fade_len:] * fade_in + post[:fade_len] * fade_out
                    processed[start_sample : start_sample + fade_len] = repair

                    # Fill any remaining with appropriate content
                    remaining = (end_sample - start_sample) - fade_len
                    if remaining > 0:
                        processed[start_sample + fade_len : end_sample] = 0.0

        return processed


class BeatAlignmentStage:
    """Stage 6: Detect beats and optionally align to grid."""

    def __init__(self, mode: str = "analyze", target_bpm: Optional[float] = None):
        self.mode = mode
        self.target_bpm = target_bpm

    def process(self, result: StageResult) -> StageResult:
        """Analyze beats and optionally align timing."""
        audio = result.audio
        sr = result.sample_rate

        # Detect beats
        tempo, beat_frames = librosa.beat.beat_track(y=audio, sr=sr)
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)

        # Calculate tempo curve (drift over time)
        if len(beat_times) > 2:
            beat_intervals = np.diff(beat_times)
            instantaneous_bpm = 60.0 / beat_intervals
        else:
            instantaneous_bpm = np.array([tempo])

        beat_info = {
            "average_bpm": float(tempo),
            "beat_times": beat_times.tolist(),
            "beat_count": len(beat_times),
            "tempo_stability": float(np.std(instantaneous_bpm))
            if len(instantaneous_bpm) > 1
            else 0.0,
            "instantaneous_bpm": instantaneous_bpm.tolist()
            if len(instantaneous_bpm) > 1
            else [float(tempo)],
        }

        if self.mode == "analyze":
            # Just report, don't modify
            metadata = result.metadata.copy()
            metadata["beat_analysis"] = beat_info

            report = {
                "stage": "beat_alignment",
                "mode": "analyze",
                "bpm": float(tempo),
                "beat_count": len(beat_times),
                "tempo_stability": beat_info["tempo_stability"],
                "status": "success",
            }

            return StageResult(audio, sr, metadata, report)

        else:  # align mode
            # TODO: Implement time stretching to align to target BPM
            # This is complex and should be implemented carefully
            # For now, just report what would be done

            metadata = result.metadata.copy()
            metadata["beat_analysis"] = beat_info
            metadata["target_bpm"] = self.target_bpm or tempo

            report = {
                "stage": "beat_alignment",
                "mode": "align",
                "bpm": float(tempo),
                "target_bpm": self.target_bpm or tempo,
                "note": "Time stretching not yet implemented in align mode",
                "status": "partial",
            }

            return StageResult(audio, sr, metadata, report)


class FinalAssemblyStage:
    """Stage 7: Final normalization, metadata embedding, and export."""

    def __init__(self, target_lufs: float = -16.0, output_format: str = "wav"):
        self.target_lufs = target_lufs
        self.output_format = output_format

    def process(self, result: StageResult, all_reports: List[Dict]) -> Tuple[str, Dict]:
        """Apply final processing and export."""
        audio = result.audio
        sr = result.sample_rate

        # Normalize to target LUFS (simplified - real LUFS requires more complex calculation)
        # For now, use peak normalization as approximation
        peak = np.max(np.abs(audio))
        if peak > 0:
            # Target peak at -1 dBFS
            target_peak = 10 ** (-1 / 20)
            audio = audio * (target_peak / peak)

        # Gentle limiting
        audio = np.clip(audio, -0.99, 0.99)

        # Generate output path
        from pathlib import Path
        import time

        timestamp = int(time.time())
        output_path = f"cleaned_{timestamp}.{self.output_format}"

        # Export
        sf.write(output_path, audio, sr, subtype="PCM_24")

        # Compile summary report
        summary = {
            "output_file": output_path,
            "duration": len(audio) / sr,
            "sample_rate": sr,
            "format": self.output_format,
            "stages_applied": len(all_reports),
            "stage_reports": all_reports,
            "original_bpm": result.metadata.get("bpm"),
            "original_key": result.metadata.get("key"),
            "processing_timestamp": timestamp,
            "status": "success",
        }

        return output_path, summary
