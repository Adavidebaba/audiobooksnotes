from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, Any, List

from src.store import StoreManager


class QuoteUpdateRequest(BaseModel):
    """Pydantic model representing a request to update a quote and its confidence."""
    libraryItemId: str
    createdAt: int
    quote: str
    quote_confidence: str


class QuoteDeleteRequest(BaseModel):
    """Pydantic model representing a request to delete a quote."""
    libraryItemId: str
    createdAt: int


class QuoteReprocessRequest(BaseModel):
    """Pydantic model representing a request to reprocess a single quote."""
    libraryItemId: str
    createdAt: int


class WebServer:
    """Class responsible for initializing, routing, and exposing the FastAPI server."""

    def __init__(self, coordinator) -> None:
        """Initializes the WebServer with the OrchestrationCoordinator instance."""
        self.coordinator = coordinator
        self.store_mgr = coordinator.store_mgr
        self.app = FastAPI(
            title="AudiobookNotes Dashboard",
            description="Web interface to view, filter, edit, and delete audiobooks notes and quotes."
        )
        self._setup_routes()

    def _setup_routes(self) -> None:
        """Sets up API endpoints and mounts the static files folder."""
        
        @self.app.get("/api/quotes")
        def get_quotes() -> List[Dict[str, Any]]:
            """API endpoint to retrieve all aggregated book quotes."""
            return self.store_mgr.get_all_quotes()

        @self.app.put("/api/quotes")
        def update_quote(request: QuoteUpdateRequest) -> Dict[str, Any]:
            """API endpoint to update a quote and its confidence level."""
            success = self.store_mgr.update_quote(
                library_item_id=request.libraryItemId,
                created_at=request.createdAt,
                new_quote=request.quote,
                new_confidence=request.quote_confidence
            )
            if not success:
                raise HTTPException(status_code=404, detail="Citazione non trovata o aggiornamento fallito.")
            return {"status": "success", "message": "Citazione aggiornata con successo."}

        @self.app.delete("/api/quotes")
        def delete_quote(request: QuoteDeleteRequest) -> Dict[str, Any]:
            """API endpoint to delete a specific quote from a book JSON."""
            success = self.store_mgr.delete_quote(
                library_item_id=request.libraryItemId,
                created_at=request.createdAt
            )
            if not success:
                raise HTTPException(status_code=404, detail="Citazione non trovata o eliminazione fallita.")
            return {"status": "success", "message": "Citazione eliminata con successo."}

        @self.app.post("/api/poll")
        def trigger_manual_poll() -> Dict[str, Any]:
            """API endpoint to trigger an immediate manual polling check for new Audiobookshelf bookmarks and YouTube links."""
            import threading
            threading.Thread(target=self.coordinator.run_single_poll, daemon=True).start()
            return {"status": "success", "message": "Controllo nuovi contenuti avviato in background."}

        @self.app.post("/api/reprocess")
        def reprocess_all() -> Dict[str, Any]:
            """API endpoint to trigger a complete re-processing of all bookmarks from scratch."""
            self.coordinator.reset_and_reprocess_all()
            return {"status": "success", "message": "Riprocessamento avviato in background."}

        @self.app.post("/api/quotes/reprocess")
        def reprocess_single_quote(request: QuoteReprocessRequest) -> Dict[str, Any]:
            """API endpoint to trigger a single bookmark re-processing with 20% expanded window."""
            updated_quote = self.coordinator.reprocess_single_quote(
                library_item_id=request.libraryItemId,
                created_at=request.createdAt
            )
            if not updated_quote:
                raise HTTPException(
                    status_code=404, 
                    detail="Impossibile rielaborare la citazione. Controlla la connessione ad Audiobookshelf o i log del server."
                )
            return updated_quote

        # Serve frontend static assets (HTML, CSS, JS)
        static_dir = Path(__file__).parent / "static"
        static_dir.mkdir(parents=True, exist_ok=True)
        self.app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
