import httpx
from datetime import datetime
from typing import Dict, List, Any, Optional

class ReadwiseManager:
    """Manager responsible for formatting and sending highlights to the Readwise API (v2)."""

    BASE_URL = "https://readwise.io/api/v2"

    def __init__(self, api_token: str) -> None:
        """Initializes ReadwiseManager with the given API token."""
        self.api_token = api_token.strip() if api_token else ""
        self.headers = {
            "Authorization": f"Token {self.api_token}",
            "Content-Type": "application/json"
        }

    @property
    def is_configured(self) -> bool:
        """Returns True if an API token is provided."""
        return bool(self.api_token)

    def verify_token(self) -> bool:
        """Verifies if the Readwise API token is valid using /api/v2/auth/."""
        if not self.is_configured:
            return False
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    f"{self.BASE_URL}/auth/",
                    headers={"Authorization": f"Token {self.api_token}"}
                )
                return response.status_code == 204
        except httpx.HTTPError:
            return False

    def format_highlight(self, quote: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Transforms an internal quote entry into a Readwise-compliant highlight dictionary."""
        text = quote.get("quote") or quote.get("transcript")
        if not text or not str(text).strip():
            return None

        source_type = quote.get("source_type", "audiobook")
        is_youtube = source_type == "youtube"
        
        category = "articles" if is_youtube else "books"
        source_label = "youtube" if is_youtube else "audiobook"

        # Determine timestamp / date
        created_at = quote.get("createdAt", 0)
        if created_at and created_at > 0:
            highlighted_at = datetime.utcfromtimestamp(created_at / 1000.0).strftime("%Y-%m-%d %H:%M:%SZ")
        else:
            highlighted_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%SZ")

        # Format note / context
        notes_parts = []
        if quote.get("title"):
            notes_parts.append(f"Bookmark: {quote.get('title')}")
        if quote.get("quote_reasoning"):
            notes_parts.append(f"Contesto: {quote.get('quote_reasoning')}")
        note_str = " | ".join(notes_parts) if notes_parts else None

        highlight = {
            "text": str(text).strip(),
            "title": quote.get("bookTitle") or "Senza Titolo",
            "author": quote.get("bookAuthor") or "Autore Sconosciuto",
            "source_type": source_label,
            "category": category,
            "location": int(quote.get("time", 0)),
            "location_type": "offset",
            "highlighted_at": highlighted_at
        }

        if quote.get("video_url"):
            highlight["source_url"] = quote.get("video_url")
        if note_str:
            highlight["note"] = note_str

        return highlight

    def send_highlights(self, highlights: List[Dict[str, Any]]) -> bool:
        """Sends a list of formatted highlights to Readwise in batches of up to 100 items."""
        if not self.is_configured or not highlights:
            return False

        chunk_size = 100
        url = f"{self.BASE_URL}/highlights/"

        with httpx.Client(timeout=20.0) as client:
            for i in range(0, len(highlights), chunk_size):
                chunk = highlights[i:i + chunk_size]
                payload = {"highlights": chunk}
                response = client.post(url, headers=self.headers, json=payload)
                response.raise_for_status()

        return True

    def sync_single_quote(self, quote: Dict[str, Any]) -> bool:
        """Helper to format and send a single quote to Readwise immediately."""
        highlight = self.format_highlight(quote)
        if not highlight:
            return False
        try:
            return self.send_highlights([highlight])
        except Exception as e:
            print(f"[Readwise] Errore sincronizzazione singola citazione: {e}")
            return False

    def sync_quotes_batch(self, quotes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Filters valid quotes, formats highlights, and sends them to Readwise."""
        valid_items = []
        for q in quotes:
            h = self.format_highlight(q)
            if h:
                valid_items.append((q, h))

        if not valid_items:
            return {"synced_count": 0, "total": len(quotes), "success": True}

        highlights_to_send = [item[1] for item in valid_items]
        try:
            self.send_highlights(highlights_to_send)
            return {
                "synced_count": len(valid_items),
                "total": len(quotes),
                "success": True,
                "synced_quotes": [item[0] for item in valid_items]
            }
        except Exception as e:
            print(f"[Readwise] Errore sincronizzazione batch: {e}")
            return {
                "synced_count": 0,
                "total": len(quotes),
                "success": False,
                "error": str(e)
            }
