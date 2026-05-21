import subprocess
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple

class AudioManager:
    """Manager responsible for calculating, extracting, and concatenating audio segments using ffmpeg."""

    def __init__(self, base_url: str, abs_token: str, temp_dir: Path) -> None:
        """Initializes AudioManager with ABS base URL, ABS API Token and a directory for temporary audio files."""
        self.base_url = base_url.rstrip("/")
        self.abs_token = abs_token
        self.temp_dir = temp_dir
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def calculate_window(
        self, 
        bookmark_time: float, 
        pre_seconds: int, 
        post_seconds: int, 
        total_duration: float
    ) -> Tuple[float, float]:
        """Calculates the time window to extract and clamps it to the total book duration."""
        start = max(0.0, bookmark_time - pre_seconds)
        end = min(total_duration, bookmark_time + post_seconds)
        return start, end

    def get_overlapping_tracks(
        self, 
        start_time: float, 
        end_time: float, 
        tracks: List[Dict[str, Any]]
    ) -> List[Tuple[Dict[str, Any], float, float]]:
        """Identifies tracks that overlap with the window and computes local start/end times."""
        overlapping = []
        for track in tracks:
            # startOffset and duration define track range in seconds
            start_offset = float(track.get("startOffset", 0.0))
            duration = float(track.get("duration", 0.0))
            track_end = start_offset + duration

            # Check overlap
            if start_offset < end_time and track_end > start_time:
                local_start = max(0.0, start_time - start_offset)
                local_end = min(duration, end_time - start_offset)
                overlapping.append((track, local_start, local_end))
        return overlapping

    def _extract_single_segment(
        self, 
        content_url: str, 
        start: float, 
        end: float, 
        output_path: Path
    ) -> None:
        """Runs ffmpeg to extract a specific segment of audio directly from a URL."""
        headers_arg = f"Authorization: Bearer {self.abs_token}\r\n"
        
        # Fast input seeking (-ss before -i)
        cmd = [
            "ffmpeg",
            "-headers", headers_arg,
            "-ss", f"{start:.3f}",
            "-to", f"{end:.3f}",
            "-i", content_url,
            "-vn",
            "-ac", "1",
            "-ar", "16000",
            "-b:a", "32k",
            "-y",
            "-f", "mp3",
            str(output_path)
        ]
        
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            stderr_out = result.stderr.decode("utf-8", errors="ignore")
            raise RuntimeError(f"ffmpeg extraction failed: {stderr_out}")

    def _concatenate_segments(self, segment_paths: List[Path], output_path: Path) -> None:
        """Runs ffmpeg to concatenate multiple local audio segments."""
        if not segment_paths:
            raise ValueError("No segments to concatenate")
        
        # Construct filter complex argument: [0:a][1:a]...concat=n=N:v=0:a=1
        inputs = []
        filter_complex_inputs = ""
        for i, path in enumerate(segment_paths):
            inputs.extend(["-i", str(path)])
            filter_complex_inputs += f"[{i}:a]"
            
        filter_complex = f"{filter_complex_inputs}concat=n={len(segment_paths)}:v=0:a=1"
        
        cmd = [
            "ffmpeg",
            *inputs,
            "-filter_complex", filter_complex,
            "-y",
            "-f", "mp3",
            str(output_path)
        ]
        
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            stderr_out = result.stderr.decode("utf-8", errors="ignore")
            raise RuntimeError(f"ffmpeg concatenation failed: {stderr_out}")

    def extract_audio(
        self, 
        bookmark_id: str,
        bookmark_time: float, 
        pre_seconds: int, 
        post_seconds: int, 
        tracks: List[Dict[str, Any]],
        total_duration: float
    ) -> Path:
        """Main method: extracts the audio window and returns the path to the consolidated audio file."""
        start_time, end_time = self.calculate_window(bookmark_time, pre_seconds, post_seconds, total_duration)
        overlapping = self.get_overlapping_tracks(start_time, end_time, tracks)
        
        if not overlapping:
            raise ValueError("No audio tracks found overlapping with the bookmark window")
            
        final_output_path = self.temp_dir / f"{bookmark_id}_{round(bookmark_time, 3)}.mp3"
        
        # If window fits inside a single track, extract it directly
        if len(overlapping) == 1:
            track, local_start, local_end = overlapping[0]
            content_url = track.get("contentUrl", "")
            if content_url.startswith("/"):
                content_url = f"{self.base_url}{content_url}"
            self._extract_single_segment(content_url, local_start, local_end, final_output_path)
            return final_output_path
            
        # Multi-track overlap: extract segments and concatenate
        segment_paths = []
        for i, (track, local_start, local_end) in enumerate(overlapping):
            seg_path = self.temp_dir / f"{bookmark_id}_part{i}.mp3"
            content_url = track.get("contentUrl", "")
            if content_url.startswith("/"):
                content_url = f"{self.base_url}{content_url}"
            self._extract_single_segment(content_url, local_start, local_end, seg_path)
            segment_paths.append(seg_path)
            
        try:
            self._concatenate_segments(segment_paths, final_output_path)
        finally:
            # Clean up intermediate segment files
            for seg_path in segment_paths:
                if seg_path.exists():
                    try:
                        os.remove(seg_path)
                    except OSError:
                        pass
                        
        return final_output_path
