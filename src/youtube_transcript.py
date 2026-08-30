from typing import Optional, Dict, Any
from youtube_transcript_api import YouTubeTranscriptApi


class YouTubeTranscriptManager:
    """Manager responsible for downloading YouTube subtitles and extracting text windows."""

    def __init__(self, pre_seconds: int = 60, post_seconds: int = 60) -> None:
        """Initializes the manager with default window sizes."""
        self.pre_seconds = pre_seconds
        self.post_seconds = post_seconds

    def get_transcript_window(
        self,
        video_id: str,
        timestamp: int,
        pre_seconds: Optional[int] = None,
        post_seconds: Optional[int] = None
    ) -> Dict[str, Any]:
        """Downloads subtitles and extracts text around the given timestamp.

        Returns:
            Dict with keys:
                - 'transcript': str or None (the extracted text window)
                - 'available': bool (whether subtitles were found)
                - 'error_message': str (description if subtitles unavailable)
                - 'video_title': str (empty, populated later by caller)
        """
        effective_pre = pre_seconds if pre_seconds is not None else self.pre_seconds
        effective_post = post_seconds if post_seconds is not None else self.post_seconds

        try:
            transcript_entries = YouTubeTranscriptApi.get_transcript(
                video_id,
                languages=["it", "en", "en-US", "en-GB"]
            )
        except Exception as exc:
            return {
                "transcript": None,
                "available": False,
                "error_message": f"Subtitles not available: {type(exc).__name__}: {str(exc)}"
            }

        return self._extract_window(transcript_entries, timestamp, effective_pre, effective_post)

    def _extract_window(
        self,
        entries: list,
        timestamp: int,
        pre_seconds: int,
        post_seconds: int
    ) -> Dict[str, Any]:
        """Filters subtitle entries to the time window and joins them into a single text block."""
        window_start = max(0, timestamp - pre_seconds)
        window_end = timestamp + post_seconds

        window_entries = []
        for entry in entries:
            entry_start = entry.get("start", 0)
            entry_end = entry_start + entry.get("duration", 0)

            # Include entry if it overlaps with the window
            if entry_end >= window_start and entry_start <= window_end:
                window_entries.append(entry)

        if not window_entries:
            return {
                "transcript": None,
                "available": True,
                "error_message": "No subtitle entries found in the specified time window."
            }

        text_parts = [entry.get("text", "") for entry in window_entries]
        combined_text = " ".join(text_parts).strip()

        return {
            "transcript": combined_text if combined_text else None,
            "available": True,
            "error_message": ""
        }
