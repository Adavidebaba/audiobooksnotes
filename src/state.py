import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Set

class StateManager:
    """Manages local state serialization, persistence, and bookmark status comparison."""

    def __init__(self, state_file_path: Path) -> None:
        """Initializes StateManager with the target path for the state file."""
        self.state_file_path = state_file_path
        self.state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        """Loads state from file, or returns a blank new state structure if not found/invalid."""
        if not self.state_file_path.exists():
            return {"version": 1, "bookmarks": {}, "youtube_processed": {}}
        try:
            with open(self.state_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Ensure youtube_processed section exists (backward compatibility)
                if "youtube_processed" not in data:
                    data["youtube_processed"] = {}
                return data
        except (json.JSONDecodeError, IOError):
            # Back up corrupted file and return fresh
            backup_path = self.state_file_path.with_suffix(".corrupted")
            if self.state_file_path.exists():
                os.replace(self.state_file_path, backup_path)
            return {"version": 1, "bookmarks": {}, "youtube_processed": {}}

    def save_state(self) -> None:
        """Persists the current state atomically using a temporary file."""
        temp_path = self.state_file_path.with_suffix(".tmp")
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False)
            os.replace(temp_path, self.state_file_path)
        except IOError as e:
            if temp_path.exists():
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
            raise e

    def get_bookmark_key(self, library_item_id: str, bookmark_time: float) -> str:
        """Generates a stable string key for a bookmark based on library ID and time (rounded)."""
        return f"{library_item_id}:{round(bookmark_time, 3)}"

    def get_unprocessed_bookmarks(
        self, 
        current_bookmarks: List[Dict[str, Any]], 
        bootstrap_mode: str, 
        bootstrap_since_iso: str = "",
        ignore_bootstrap: bool = False
    ) -> List[Dict[str, Any]]:
        """Compares list of bookmarks from ABS with local state and returns bookmarks to process."""
        unprocessed = []
        is_first_run = len(self.state.get("bookmarks", {})) == 0 and not ignore_bootstrap

        # Parse bootstrap date if in 'since' mode
        since_ms = 0
        if bootstrap_mode == "since" and bootstrap_since_iso:
            try:
                dt = datetime.fromisoformat(bootstrap_since_iso.replace("Z", "+00:00"))
                since_ms = int(dt.timestamp() * 1000)
            except ValueError:
                pass

        for bm in current_bookmarks:
            item_id = bm.get("libraryItemId", "")
            bm_time = bm.get("time", 0.0)
            created_at = bm.get("createdAt", 0)
            key = self.get_bookmark_key(item_id, bm_time)
            
            # Check if already processed and marked ok or skipped
            bm_state = self.state["bookmarks"].get(key)
            if bm_state and bm_state.get("status") in ("ok", "skipped", "skipped_since"):
                continue

            # Apply Bootstrap Mode rules on first run
            if is_first_run:
                if bootstrap_mode == "skip":
                    self.mark_processed(bm, "skipped")
                    continue
                elif bootstrap_mode == "since" and created_at < since_ms:
                    self.mark_processed(bm, "skipped_since")
                    continue

            unprocessed.append(bm)
            
        if is_first_run and (bootstrap_mode == "skip" or bootstrap_mode == "since"):
            self.save_state()

        return unprocessed

    def mark_processed(
        self, 
        bookmark: Dict[str, Any], 
        status: str, 
        pre_seconds: int = 30, 
        post_seconds: int = 30, 
        error_msg: str = None
    ) -> None:
        """Marks a bookmark as processed or failed in the state."""
        item_id = bookmark.get("libraryItemId", "")
        bm_time = bookmark.get("time", 0.0)
        key = self.get_bookmark_key(item_id, bm_time)

        entry = {
            "libraryItemId": item_id,
            "time": bm_time,
            "title": bookmark.get("title", ""),
            "createdAt": bookmark.get("createdAt", 0),
            "processed_at": datetime.utcnow().isoformat() + "Z",
            "audio_window": {"pre": pre_seconds, "post": post_seconds},
            "status": status
        }
        if error_msg:
            entry["error"] = error_msg

        self.state["bookmarks"][key] = entry

    # --- YouTube link tracking ---

    def get_youtube_link_key(self, video_id: str, timestamp: int) -> str:
        """Generates a stable string key for a YouTube link based on video ID and timestamp."""
        return f"{video_id}:{timestamp}"

    def is_youtube_link_processed(self, video_id: str, timestamp: int) -> bool:
        """Checks whether a YouTube link has already been processed."""
        key = self.get_youtube_link_key(video_id, timestamp)
        yt_state = self.state.get("youtube_processed", {}).get(key)
        return yt_state is not None and yt_state.get("status") in ("ok", "failed")

    def mark_youtube_link_processed(
        self,
        video_id: str,
        timestamp: int,
        raw_url: str,
        status: str,
        error_msg: str = None
    ) -> None:
        """Marks a YouTube link as processed or failed in the state."""
        key = self.get_youtube_link_key(video_id, timestamp)
        entry = {
            "video_id": video_id,
            "timestamp": timestamp,
            "raw_url": raw_url,
            "processed_at": datetime.utcnow().isoformat() + "Z",
            "status": status
        }
        if error_msg:
            entry["error"] = error_msg

        self.state["youtube_processed"][key] = entry

    def clear_state(self) -> None:
        """Clears all historical records in the state and saves it."""
        self.state = {"version": 1, "bookmarks": {}, "youtube_processed": {}}
        self.save_state()
