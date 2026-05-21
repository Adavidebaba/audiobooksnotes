import sys
import time
import traceback
from pathlib import Path
from typing import Dict, Any, List

from src.config import ConfigManager
from src.abs_client import AbsClientManager
from src.state import StateManager
from src.audio import AudioManager
from src.stt import SttManager
from src.llm import LlmManager
from src.store import StoreManager

class OrchestrationCoordinator:
    """Coordinator responsible for orchestrating the overall polling workflow and error handling."""

    def __init__(self, config: ConfigManager) -> None:
        """Initializes the orchestrator with all necessary sub-managers."""
        self.config = config
        self.abs_client = AbsClientManager(config.abs_url, config.abs_token)
        self.state_mgr = StateManager(config.state_file_path)
        self.audio_mgr = AudioManager(config.abs_url, config.abs_token, config.data_dir / "tmp")
        self.stt_mgr = SttManager(config.openrouter_api_key, config.openrouter_stt_model)
        self.llm_mgr = LlmManager(config.openrouter_api_key, config.openrouter_llm_model)
        self.store_mgr = StoreManager(config.books_dir)

    def close(self) -> None:
        """Cleans up active resources."""
        self.abs_client.close()

    def run_single_poll(self) -> None:
        """Retrieves and processes any new or failed bookmarks from Audiobookshelf."""
        print("Polling Audiobookshelf per rilevare nuovi bookmark...")
        try:
            current_bookmarks = self.abs_client.get_bookmarks()
        except Exception as e:
            print(f"Errore durante il recupero dei bookmark da ABS: {e}")
            return

        unprocessed = self.state_mgr.get_unprocessed_bookmarks(
            current_bookmarks, 
            self.config.bootstrap_mode, 
            self.config.bootstrap_since_iso
        )

        if not unprocessed:
            print("Nessun nuovo bookmark da elaborare.")
            return

        print(f"Rilevati {len(unprocessed)} nuovi bookmark da elaborare.")
        for bm in unprocessed:
            self._process_bookmark_with_retry(bm)

    def _process_bookmark_with_retry(self, bookmark: Dict[str, Any], max_retries: int = 3) -> None:
        """Attempts to process a bookmark, applying exponential backoff for transient failures."""
        library_item_id = bookmark.get("libraryItemId", "")
        bm_time = bookmark.get("time", 0.0)
        
        print(f"\n[Elaborazione] Libro {library_item_id} al tempo {bm_time}s...")
        
        backoff = 2.0
        for attempt in range(1, max_retries + 1):
            try:
                self._execute_pipeline(bookmark)
                # Success, write ok state
                self.state_mgr.mark_processed(
                    bookmark, 
                    "ok", 
                    self.config.pre_seconds, 
                    self.config.post_seconds
                )
                self.state_mgr.save_state()
                print(f"[Completato] Bookmark {library_item_id}:{bm_time}s salvato con successo.")
                return
            except Exception as e:
                print(f"Tentativo {attempt}/{max_retries} fallito per bookmark {library_item_id}:{bm_time}s. Errore: {e}")
                
                # Check for permanent errors (like invalid key, authorization etc)
                if "401" in str(e) or "404" in str(e) or "Unauthorized" in str(e):
                    print("[Errore Permanente] Interruzione immediata dei tentativi.")
                    self.state_mgr.mark_processed(
                        bookmark, 
                        "failed", 
                        self.config.pre_seconds, 
                        self.config.post_seconds,
                        error_msg=str(e)
                    )
                    self.state_mgr.save_state()
                    return
                
                if attempt < max_retries:
                    time.sleep(backoff)
                    backoff *= 2
                    
        # If all retries failed, leave it unprocessed so it will be retried on next poll loop
        print(f"[Riprova in seguito] Bookmark {library_item_id}:{bm_time}s non elaborato. Sarà ritentato al prossimo poll.")

    def _execute_pipeline(self, bookmark: Dict[str, Any]) -> None:
        """Executes the extraction, transcription, LLM quote matching, and storage pipeline."""
        library_item_id = bookmark.get("libraryItemId", "")
        bm_time = bookmark.get("time", 0.0)
        bm_title = bookmark.get("title", "")
        
        # 1. Fetch metadata
        meta = self.abs_client.get_item_metadata(library_item_id)
        media = meta.get("media", {})
        tracks = media.get("tracks", [])
        duration = float(media.get("duration", 0.0))
        
        # 2. Extract audio
        audio_file_path = None
        try:
            audio_file_path = self.audio_mgr.extract_audio(
                bookmark_id=library_item_id,
                bookmark_time=bm_time,
                pre_seconds=self.config.pre_seconds,
                post_seconds=self.config.post_seconds,
                tracks=tracks,
                total_duration=duration
            )
            
            # 3. Transcribe audio
            print(f"Avvio trascrizione con Whisper API per {audio_file_path.name}...")
            transcript = self.stt_mgr.transcribe_audio(audio_file_path, self.config.language)
            
            # 4. Extract quote using LLM
            quote_data = {"quote": None, "confidence": "low", "reasoning": "La trascrizione è vuota."}
            if transcript.strip():
                item_metadata = media.get("metadata", {})
                book_title = item_metadata.get("title", "Titolo Sconosciuto")
                book_author = item_metadata.get("authorName", "Autore Sconosciuto")
                
                print(f"Estrazione citazione con {self.config.openrouter_llm_model}...")
                quote_data = self.llm_mgr.extract_verbatim_quote(
                    transcript=transcript,
                    book_title=book_title,
                    author=book_author,
                    bookmark_title=bm_title
                )
            
            # 5. Append to book-specific JSON file
            self.store_mgr.append_quote_to_book(
                library_item_id=library_item_id,
                metadata=meta,
                bookmark=bookmark,
                transcript=transcript,
                quote_data=quote_data,
                pre_seconds=self.config.pre_seconds,
                post_seconds=self.config.post_seconds
            )
        finally:
            # 6. Ensure temporary audio file cleanup
            if audio_file_path and audio_file_path.exists():
                try:
                    Path(audio_file_path).unlink()
                except OSError:
                    pass

def main() -> None:
    """Entry point of the application."""
    print("=== Inizializzazione AudiobookNotes ===")
    try:
        config = ConfigManager()
        coordinator = OrchestrationCoordinator(config)
    except Exception as e:
        print(f"ERRORE DI CONFIGURAZIONE ALL'AVVIO: {e}")
        traceback.print_exc()
        sys.exit(1)
        
    print(f"Servizio avviato con successo. Intervallo di polling: {config.poll_interval_seconds}s.")
    print(f"Modalità Bootstrap: {config.bootstrap_mode}")
    
    try:
        while True:
            coordinator.run_single_poll()
            time.sleep(config.poll_interval_seconds)
    except KeyboardInterrupt:
        print("\nServizio interrotto dall'utente. Spegnimento in corso...")
    finally:
        coordinator.close()
        print("Arrivederci!")

if __name__ == "__main__":
    main()
