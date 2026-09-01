import json
import urllib.request
from typing import Optional, Dict, Any
from youtube_transcript_api import YouTubeTranscriptApi


class YouTubeTranscriptManager:
    """Manager responsible for downloading YouTube subtitles, metadata, and extracting text windows."""

    def __init__(self, pre_seconds: int = 60, post_seconds: int = 60) -> None:
        """Initializes the manager with default window sizes."""
        self.pre_seconds = pre_seconds
        self.post_seconds = post_seconds
        self._api = YouTubeTranscriptApi() if callable(YouTubeTranscriptApi) else YouTubeTranscriptApi

    @staticmethod
    def get_video_metadata(video_id: str) -> Dict[str, str]:
        """Fetches public video metadata (title, author/channel name) via YouTube oEmbed API."""
        oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        try:
            req = urllib.request.Request(
                oembed_url, 
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    return {
                        "title": data.get("title", f"YouTube: {video_id}"),
                        "author": data.get("author_name", "YouTube")
                    }
        except Exception:
            pass
        return {
            "title": f"YouTube: {video_id}",
            "author": "YouTube"
        }

    def _fetch_entries(self, video_id: str) -> list:
        """Fetches raw subtitle entries from YouTube Transcript API with language fallbacks."""
        if hasattr(self._api, "fetch"):
            try:
                return self._api.fetch(video_id, languages=["it", "en", "en-US", "en-GB"])
            except Exception:
                if hasattr(self._api, "list"):
                    transcript_list = self._api.list(video_id)
                    try:
                        transcript_obj = transcript_list.find_transcript(["it", "en", "en-US", "en-GB"])
                    except Exception:
                        transcript_obj = next(iter(transcript_list), None)
                    if transcript_obj:
                        return transcript_obj.fetch()
        elif hasattr(YouTubeTranscriptApi, "get_transcript"):
            return YouTubeTranscriptApi.get_transcript(
                video_id,
                languages=["it", "en", "en-US", "en-GB"]
            )
        else:
            api_instance = YouTubeTranscriptApi()
            return api_instance.fetch(video_id, languages=["it", "en", "en-US", "en-GB"])
        return []

    def get_full_transcript(self, video_id: str) -> Dict[str, Any]:
        """Downloads complete subtitles for the entire video.

        Returns:
            Dict with keys 'transcript', 'available', and 'error_message'.
        """
        try:
            entries = self._fetch_entries(video_id)
        except Exception as exc:
            return {
                "transcript": None,
                "available": False,
                "error_message": f"Subtitles not available: {type(exc).__name__}: {str(exc)}"
            }

        if not entries:
            return {
                "transcript": None,
                "available": False,
                "error_message": "No subtitle entries found for this video."
            }

        all_text_parts = []
        for entry in entries:
            text = getattr(entry, "text", entry.get("text", "") if isinstance(entry, dict) else "")
            if text and text.strip():
                all_text_parts.append(text.strip())

        combined = " ".join(all_text_parts).strip()
        return {
            "transcript": combined if combined else None,
            "available": bool(combined),
            "error_message": "" if combined else "Subtitles empty."
        }

    def get_transcript_window(
        self,
        video_id: str,
        timestamp: int,
        pre_seconds: Optional[int] = None,
        post_seconds: Optional[int] = None
    ) -> Dict[str, Any]:
        """Downloads subtitles and extracts text around the given timestamp.

        Returns:
            Dict with keys 'transcript', 'available', and 'error_message'.
        """
        effective_pre = pre_seconds if pre_seconds is not None else self.pre_seconds
        effective_post = post_seconds if post_seconds is not None else self.post_seconds

        try:
            entries = self._fetch_entries(video_id)
        except Exception as exc:
            return {
                "transcript": None,
                "available": False,
                "error_message": f"Subtitles not available: {type(exc).__name__}: {str(exc)}"
            }

        return self._extract_window(entries, timestamp, effective_pre, effective_post)

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
            entry_start = getattr(entry, "start", entry.get("start", 0) if isinstance(entry, dict) else 0)
            entry_duration = getattr(entry, "duration", entry.get("duration", 0) if isinstance(entry, dict) else 0)
            entry_text = getattr(entry, "text", entry.get("text", "") if isinstance(entry, dict) else "")
            entry_end = entry_start + entry_duration

            # Include entry if it overlaps with the window
            if entry_end >= window_start and entry_start <= window_end:
                window_entries.append(entry_text)

        if not window_entries:
            return {
                "transcript": None,
                "available": True,
                "error_message": "No subtitle entries found in the specified time window."
            }

        combined_text = " ".join(window_entries).strip()

        return {
            "transcript": combined_text if combined_text else None,
            "available": True,
            "error_message": ""
        }
