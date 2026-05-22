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

    def _deduplicate_bookmarks(self, bookmarks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicates a list of bookmarks by createdAt or time, keeping the first occurrence."""
        seen_created_ats = set()
        seen_times = set()
        unique_bookmarks = []
        for bm in bookmarks:
            c_at = bm.get("createdAt", 0)
            t = bm.get("time", 0.0)
            
            if c_at > 0:
                if c_at in seen_created_ats:
                    continue
                seen_created_ats.add(c_at)
            else:
                if t in seen_times:
                    continue
                seen_times.add(t)
            unique_bookmarks.append(bm)
        return unique_bookmarks

    def _load_book_data(self, file_path: Path, library_item_id: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Loads existing book data or returns a default template initialized with metadata."""
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "bookmarks" in data:
                        data["bookmarks"] = self._deduplicate_bookmarks(data["bookmarks"])
                    return data
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
        """Appends a new transcribed quote entry to the book's JSON file, overwriting if duplicate."""
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
        
        # Check if bookmark already exists
        existing_index = -1
        target_created_at = bookmark.get("createdAt", 0)
        target_time = bookmark.get("time", 0.0)
        
        for i, bm in enumerate(book_data.get("bookmarks", [])):
            if (target_created_at > 0 and bm.get("createdAt") == target_created_at) or (bm.get("time") == target_time):
                existing_index = i
                break
                
        if existing_index >= 0:
            book_data["bookmarks"][existing_index] = bookmark_entry
            print(f"Aggiornata citazione esistente in {file_path.name} (Tempo: {bookmark.get('time')}s) invece di duplicare.")
        else:
            book_data["bookmarks"].append(bookmark_entry)
            print(f"Aggiunta nuova citazione in {file_path.name} (Tempo: {bookmark.get('time')}s)")
            
        book_data["updated_at"] = datetime.utcnow().isoformat() + "Z"
        self._save_book_data_atomic(file_path, book_data)

    def _find_book_file(self, library_item_id: str) -> Path | None:
        """Finds the JSON file path for a given libraryItemId using glob."""
        matching_files = list(self.books_dir.glob(f"{library_item_id}__*.json"))
        return matching_files[0] if matching_files else None

    def get_all_quotes(self) -> List[Dict[str, Any]]:
        """Scans all JSON files in books_dir and aggregates all bookmarks/quotes."""
        all_quotes = []
        for file_path in self.books_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    book_data = json.load(f)
                
                library_item_id = book_data.get("libraryItemId", "")
                book_title = book_data.get("title", "Titolo Sconosciuto")
                book_author = book_data.get("author", "Autore Sconosciuto")
                
                # Use deduplicated bookmarks
                bookmarks = self._deduplicate_bookmarks(book_data.get("bookmarks", []))
                for bookmark in bookmarks:
                    quote_entry = {
                        "libraryItemId": library_item_id,
                        "bookTitle": book_title,
                        "bookAuthor": book_author,
                        "time": bookmark.get("time", 0.0),
                        "title": bookmark.get("title", ""),
                        "createdAt": bookmark.get("createdAt", 0),
                        "processed_at": bookmark.get("processed_at", ""),
                        "audio_window": bookmark.get("audio_window", {"pre": 30, "post": 30}),
                        "transcript": bookmark.get("transcript", ""),
                        "quote": bookmark.get("quote"),
                        "quote_confidence": bookmark.get("quote_confidence", "low"),
                        "quote_reasoning": bookmark.get("quote_reasoning", "")
                    }
                    all_quotes.append(quote_entry)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Errore durante la lettura del file {file_path.name}: {e}")
                
        # Sort quotes by createdAt in descending order (newest first)
        all_quotes.sort(key=lambda x: x.get("createdAt", 0), reverse=True)
        return all_quotes

    def update_quote(
        self, 
        library_item_id: str, 
        created_at: int, 
        new_quote: str, 
        new_confidence: str
    ) -> bool:
        """Updates the text and confidence level of a specific quote in a book's JSON file."""
        file_path = self._find_book_file(library_item_id)
        if not file_path:
            return False
            
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                book_data = json.load(f)
        except (json.JSONDecodeError, IOError):
            return False
            
        updated = False
        for bookmark in book_data.get("bookmarks", []):
            if bookmark.get("createdAt") == created_at:
                bookmark["quote"] = new_quote
                bookmark["quote_confidence"] = new_confidence
                updated = True
                break
                
        if updated:
            book_data["updated_at"] = datetime.utcnow().isoformat() + "Z"
            self._save_book_data_atomic(file_path, book_data)
            return True
            
        return False

    def delete_quote(self, library_item_id: str, created_at: int) -> bool:
        """Deletes a specific bookmark entry from the book's JSON file."""
        file_path = self._find_book_file(library_item_id)
        if not file_path:
            return False
            
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                book_data = json.load(f)
        except (json.JSONDecodeError, IOError):
            return False
            
        bookmarks = book_data.get("bookmarks", [])
        initial_count = len(bookmarks)
        
        # Filter out the bookmark with matching createdAt
        book_data["bookmarks"] = [bm for bm in bookmarks if bm.get("createdAt") != created_at]
        
        if len(book_data["bookmarks"]) < initial_count:
            book_data["updated_at"] = datetime.utcnow().isoformat() + "Z"
            self._save_book_data_atomic(file_path, book_data)
            return True
            
        return False

    def get_single_quote(self, library_item_id: str, created_at: int) -> Dict[str, Any] | None:
        """Finds and returns a specific quote/bookmark entry by its library ID and createdAt timestamp."""
        file_path = self._find_book_file(library_item_id)
        if not file_path:
            return None
            
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                book_data = json.load(f)
        except (json.JSONDecodeError, IOError):
            return None
            
        for bookmark in book_data.get("bookmarks", []):
            if bookmark.get("createdAt") == created_at:
                return {
                    "libraryItemId": library_item_id,
                    "bookTitle": book_data.get("title", "Titolo Sconosciuto"),
                    "bookAuthor": book_data.get("author", "Autore Sconosciuto"),
                    **bookmark
                }
        return None

    def overwrite_quote_data(
        self, 
        library_item_id: str, 
        created_at: int, 
        transcript: str, 
        quote_data: Dict[str, Any], 
        pre_seconds: int, 
        post_seconds: int
    ) -> bool:
        """Overwrites the full quote details, transcript, and audio window for a specific bookmark."""
        file_path = self._find_book_file(library_item_id)
        if not file_path:
            return False
            
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                book_data = json.load(f)
        except (json.JSONDecodeError, IOError):
            return False
            
        updated = False
        for bookmark in book_data.get("bookmarks", []):
            if bookmark.get("createdAt") == created_at:
                bookmark["transcript"] = transcript
                bookmark["quote"] = quote_data.get("quote")
                bookmark["quote_confidence"] = quote_data.get("confidence", "low")
                bookmark["quote_reasoning"] = quote_data.get("reasoning", "")
                bookmark["audio_window"] = {"pre": pre_seconds, "post": post_seconds}
                bookmark["processed_at"] = datetime.utcnow().isoformat() + "Z"
                updated = True
                break
                
        if updated:
            book_data["updated_at"] = datetime.utcnow().isoformat() + "Z"
            self._save_book_data_atomic(file_path, book_data)
            return True
            
        return False

    def clear_all_books(self) -> None:
        """Deletes all JSON files in the books directory."""
        for file_path in self.books_dir.glob("*.json"):
            try:
                file_path.unlink()
            except OSError as e:
                print(f"Impossibile rimuovere il file {file_path.name}: {e}")
