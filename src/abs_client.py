import httpx
from typing import Dict, List, Any

class AbsClientManager:
    """Manager responsible for communicating with the Audiobookshelf REST API."""

    def __init__(self, base_url: str, token: str) -> None:
        """Initializes the manager with ABS connection settings."""
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {token}"}
        # Use a persistent HTTP client for connection pooling and follow redirects
        self.client = httpx.Client(headers=self.headers, timeout=15.0, follow_redirects=True)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self) -> None:
        """Closes the underlying HTTP client."""
        self.client.close()

    def get_bookmarks(self) -> List[Dict[str, Any]]:
        """Retrieves the list of bookmarks for the current user from /api/me.
        
        Returns:
            List of bookmark dictionaries, where each bookmark has:
            - libraryItemId: str
            - title: str
            - time: float (seconds offset in book)
            - createdAt: int (epoch ms)
        """
        url = f"{self.base_url}/api/me"
        response = self.client.get(url)
        response.raise_for_status()
        
        user_data = response.json()
        return user_data.get("bookmarks", [])

    def get_item_metadata(self, library_item_id: str) -> Dict[str, Any]:
        """Retrieves expanded details of a library item from /api/items/<id>?expanded=1.
        
        Returns:
            Dictionary containing item info. Crucial keys:
            - media.tracks[]: list of audio tracks
            - media.metadata.title: str
            - media.metadata.authorName: str
            - media.metadata.narratorName: str
        """
        url = f"{self.base_url}/api/items/{library_item_id}"
        params = {"expanded": "1"}
        response = self.client.get(url, params=params)
        response.raise_for_status()
        
        return response.json()
