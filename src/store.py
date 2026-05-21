import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

class StoreManager:
    """Manager responsible for storing book-specific transcripts and quotes in JSON database files."""

    def __init__(self, books_dir: Path) -> None:
        """Initializes StoreManager with the books storage directory."""
        self.books_dir = books_dir
        self.books_dir.mkdir(parents=True, exist_ok=True)

    def _slugify(self, text: str) -> str:
        """Converts arbitrary text (like a book title) into a safe filename slug."""
        if not text:
            return "unnamed_book"
        # Keep alphanumeric characters and spaces, then replace spaces/punctuation with underscores
        slug = text.lower()
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)
        slug = re.sub(r'[\s-]+', '_', slug)
        return slug.strip('_')

    def get_book_file_path(self, library_item_id: str, title: str) -> Path:
        """Computes the target file path for a book's JSON database."""
        slug = self._slugify(title)
        filename = f"{library_item_id}__{slug}.json"
        return self.books_dir / filename

    def _load_book_data(self, file_path: Path, library_item_id: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Loads existing book data or returns a default template initialized with metadata."""
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                # If corrupted, let's keep going and back it up
                backup_path = file_path.with_suffix(".corrupted")
                os.replace(file_path, backup_path)

        media = metadata.get("media", {})
        item_metadata = media.get("metadata", {})
        
        return {
            "libraryItemId": library_item_id,
            "title": item_metadata.get("title", "Titolo Sconosciuto"),
            "author": item_metadata.get("authorName", "Autore Sconosciuto"),
            "narrator": item_metadata.get("narratorName", "Narratore Sconosciuto"),
            "updated_at": datetime.utcnow().isoformat() + "Z",
            "bookmarks": []
        }

    def _save_book_data_atomic(self, file_path: Path, data: Dict[str, Any]) -> None:
        """Writes the book JSON dictionary atomically to disk."""
        temp_path = file_path.with_suffix(".tmp")
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(temp_path, file_path)
        except IOError as e:
            if temp_path.exists():
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
            raise e

    def append_quote_to_book(
        self, 
        library_item_id: str, 
        metadata: Dict[str, Any], 
        bookmark: Dict[str, Any], 
        transcript: str, 
        quote_data: Dict[str, Any],
        pre_seconds: int = 30,
        post_seconds: int = 30
    ) -> None:
        """Appends a new transcribed quote entry to the book's JSON file."""
        media = metadata.get("media", {})
        item_metadata = media.get("metadata", {})
        book_title = item_metadata.get("title", "Titolo Sconosciuto")
        
        file_path = self.get_book_file_path(library_item_id, book_title)
        book_data = self._load_book_data(file_path, library_item_id, metadata)
        
        # Build bookmark entry
        bookmark_entry = {
            "time": bookmark.get("time", 0.0),
            "title": bookmark.get("title", ""),
            "createdAt": bookmark.get("createdAt", 0),
            "processed_at": datetime.utcnow().isoformat() + "Z",
            "audio_window": {"pre": pre_seconds, "post": post_seconds},
            "transcript": transcript,
            "quote": quote_data.get("quote"),
            "quote_confidence": quote_data.get("confidence", "low"),
            "quote_reasoning": quote_data.get("reasoning", "")
        }
        
        # Append to historical records
        book_data["bookmarks"].append(bookmark_entry)
        book_data["updated_at"] = datetime.utcnow().isoformat() + "Z"
        
        self._save_book_data_atomic(file_path, book_data)
        print(f"Salvata citazione in {file_path.name} (Tempo: {bookmark.get('time')}s)")
