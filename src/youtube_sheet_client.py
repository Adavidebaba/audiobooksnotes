import re
from urllib.parse import urlparse, parse_qs
from typing import List, Dict, Any, Optional
import httpx


class YouTubeSheetClient:
    """Client responsible for reading YouTube links from a public Google Sheet via API Key."""

    SHEETS_API_BASE = "https://sheets.googleapis.com/v4/spreadsheets"

    def __init__(self, api_key: str, sheet_id: str) -> None:
        """Initializes the client with Google Sheets API credentials."""
        self.api_key = api_key
        self.sheet_id = sheet_id
        self.http_client = httpx.Client(timeout=30.0)

    def close(self) -> None:
        """Closes the underlying HTTP client."""
        self.http_client.close()

    def fetch_all_links(self) -> List[Dict[str, Any]]:
        """Reads all rows from column A of the first sheet and returns parsed YouTube link data.

        Returns:
            A list of dicts with keys: 'raw_url', 'video_id', 'timestamp', 'row_index'.
            Only valid YouTube URLs are included.
        """
        url = f"{self.SHEETS_API_BASE}/{self.sheet_id}/values/A:A"
        params = {"key": self.api_key}

        response = self.http_client.get(url, params=params)
        response.raise_for_status()

        data = response.json()
        rows = data.get("values", [])

        parsed_links = []
        for row_index, row in enumerate(rows):
            if not row or not row[0].strip():
                continue

            raw_url = row[0].strip()
            parsed = self.parse_youtube_url(raw_url)
            if parsed:
                parsed["raw_url"] = raw_url
                parsed["row_index"] = row_index
                parsed_links.append(parsed)

        return parsed_links

    @staticmethod
    def parse_youtube_url(url: str) -> Optional[Dict[str, Any]]:
        """Extracts video_id and timestamp from a YouTube URL.

        Supported formats:
            - https://youtu.be/VIDEO_ID?t=SECONDS
            - https://www.youtube.com/watch?v=VIDEO_ID&t=SECONDS
            - https://youtube.com/watch?v=VIDEO_ID (no timestamp -> 0)
            - https://www.youtube.com/live/VIDEO_ID?t=SECONDS
            - https://www.youtube.com/shorts/VIDEO_ID?t=SECONDS

        Returns:
            Dict with 'video_id' and 'timestamp' (int seconds), or None if not a valid YouTube URL.
        """
        try:
            # Strip unwanted brackets, whitespace or quotes
            cleaned_url = url.strip().strip("[]'\"").replace("[", "").replace("]", "")
            parsed = urlparse(cleaned_url)
        except Exception:
            return None

        video_id = None
        timestamp = 0

        # Format: youtu.be/VIDEO_ID
        if parsed.hostname in ("youtu.be",):
            video_id = parsed.path.lstrip("/").split("/")[0]
            query_params = parse_qs(parsed.query)
            timestamp = YouTubeSheetClient._extract_timestamp(query_params)

        # Format: youtube.com/watch?v=VIDEO_ID, /live/VIDEO_ID, or /shorts/VIDEO_ID
        elif parsed.hostname in ("www.youtube.com", "youtube.com", "m.youtube.com"):
            if parsed.path == "/watch":
                query_params = parse_qs(parsed.query)
                video_id_list = query_params.get("v", [])
                video_id = video_id_list[0] if video_id_list else None
                timestamp = YouTubeSheetClient._extract_timestamp(query_params)
            elif parsed.path.startswith("/live/"):
                video_id = parsed.path.split("/live/")[1].split("/")[0]
                query_params = parse_qs(parsed.query)
                timestamp = YouTubeSheetClient._extract_timestamp(query_params)
            elif parsed.path.startswith("/shorts/"):
                video_id = parsed.path.split("/shorts/")[1].split("/")[0].split("?")[0]
                query_params = parse_qs(parsed.query)
                timestamp = YouTubeSheetClient._extract_timestamp(query_params)

        if not video_id or len(video_id) < 5:
            return None

        return {"video_id": video_id, "timestamp": timestamp}

    @staticmethod
    def _extract_timestamp(query_params: Dict[str, list]) -> int:
        """Extracts the timestamp in seconds from URL query parameters.

        Handles formats: t=185, t=3m5s, t=1h2m3s
        """
        time_values = query_params.get("t", [])
        if not time_values:
            return 0

        raw_time = time_values[0]

        # Pure numeric seconds
        if raw_time.isdigit():
            return int(raw_time)

        # Pattern like 1h2m3s or 3m5s
        total_seconds = 0
        hours_match = re.search(r"(\d+)h", raw_time)
        minutes_match = re.search(r"(\d+)m", raw_time)
        seconds_match = re.search(r"(\d+)s", raw_time)

        if hours_match:
            total_seconds += int(hours_match.group(1)) * 3600
        if minutes_match:
            total_seconds += int(minutes_match.group(1)) * 60
        if seconds_match:
            total_seconds += int(seconds_match.group(1))

        return total_seconds
