import sys
import time
import traceback
import threading
from pathlib import Path
from typing import Dict, Any, List

import uvicorn

from src.config import ConfigManager
from src.abs_client import AbsClientManager
from src.state import StateManager
from src.audio import AudioManager
from src.stt import SttManager
from src.llm import LlmManager
from src.store import StoreManager
from src.web.server import WebServer
from src.youtube_sheet_client import YouTubeSheetClient
from src.youtube_transcript import YouTubeTranscriptManager

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
        self.poll_lock = threading.RLock()

        # YouTube (optional)
        self.yt_sheet_client = None
        self.yt_transcript_mgr = None
        if config.youtube_enabled:
            self.yt_sheet_client = YouTubeSheetClient(
                api_key=config.google_sheets_api_key,
                sheet_id=config.youtube_sheet_id
            )
            self.yt_transcript_mgr = YouTubeTranscriptManager(
                pre_seconds=config.youtube_pre_seconds,
                post_seconds=config.youtube_post_seconds
            )
            print("YouTube integration enabled.")

    def close(self) -> None:
        """Cleans up active resources."""
        self.abs_client.close()
        if self.yt_sheet_client:
            self.yt_sheet_client.close()

    def run_single_poll(self, force_bootstrap_all: bool = False) -> None:
        """Retrieves and processes any new or failed bookmarks from Audiobookshelf and YouTube."""
        with self.poll_lock:
            print("Polling Audiobookshelf per rilevare nuovi bookmark...")
            try:
                current_bookmarks = self.abs_client.get_bookmarks()
                unprocessed = self.state_mgr.get_unprocessed_bookmarks(
                    current_bookmarks=current_bookmarks, 
                    bootstrap_mode=self.config.bootstrap_mode, 
                    bootstrap_since_iso=self.config.bootstrap_since_iso,
                    ignore_bootstrap=force_bootstrap_all
                )

                if not unprocessed:
                    print("Nessun nuovo bookmark da elaborare.")
                else:
                    print(f"Rilevati {len(unprocessed)} nuovi bookmark da elaborare.")
                    for bm in unprocessed:
                        self._process_bookmark_with_retry(bm)
            except Exception as e:
                print(f"Errore durante il recupero dei bookmark da ABS: {e}")

            # YouTube polling (if enabled)
            if self.yt_sheet_client:
                self._poll_youtube_sheet()

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

    def reset_and_reprocess_all(self) -> None:
        """Clears local database and processed state, triggering an immediate background poll."""
        print("\n=== RIPROCESSO COMPLETO RICHIESTO IN BACKGROUND ===")
        
        def run_reset_and_reprocess():
            with self.poll_lock:
                print("Acquisito lock per il riprocesso completo. Inizio cancellazione database...")
                self.state_mgr.clear_state()
                self.store_mgr.clear_all_books()
                self.run_single_poll(force_bootstrap_all=True)
                
        threading.Thread(target=run_reset_and_reprocess, daemon=True).start()

    def reprocess_single_quote(self, library_item_id: str, created_at: int) -> Dict[str, Any] | None:
        """Reprocesses a single quote with 20% expanded audio window, updates store and state."""
        with self.poll_lock:
            print(f"\n=== RIPROCESSO SINGOLA CITAZIONE RICHIESTO: {library_item_id} (createdAt: {created_at}) ===")
            
            # 1. Retrieve current quote details to extract the timing and window
            current_quote = self.store_mgr.get_single_quote(library_item_id, created_at)
            if not current_quote:
                print(f"[Errore] Citazione non trovata nello store.")
                return None
                
            current_time = current_quote.get("time", 0.0)
            current_title = current_quote.get("title", "")
            
            # 2. Extract current window size or fall back to default
            current_window = current_quote.get("audio_window", {"pre": 30, "post": 30})
            current_pre = current_window.get("pre", 30)
            current_post = current_window.get("post", 30)
            
            # 3. Scale window by +20% (progressive expansion)
            new_pre = int(round(current_pre * 1.2))
            new_post = int(round(current_post * 1.2))
            
            print(f"Finestra precedente: pre={current_pre}s, post={current_post}s -> Nuova (+20%): pre={new_pre}s, post={new_post}s")
            
            # 4. Fetch metadata from ABS
            try:
                meta = self.abs_client.get_item_metadata(library_item_id)
                media = meta.get("media", {})
                tracks = media.get("tracks", [])
                duration = float(media.get("duration", 0.0))
            except Exception as e:
                print(f"[Errore] Impossibile recuperare metadati da ABS per riprocessare: {e}")
                return None
                
            # 5. Extract and process audio window
            audio_file_path = None
            try:
                audio_file_path = self.audio_mgr.extract_audio(
                    bookmark_id=library_item_id,
                    bookmark_time=current_time,
                    pre_seconds=new_pre,
                    post_seconds=new_post,
                    tracks=tracks,
                    total_duration=duration
                )
                
                # 6. Re-transcribe audio
                print(f"Rieseguo trascrizione Whisper per {audio_file_path.name}...")
                transcript = self.stt_mgr.transcribe_audio(audio_file_path, self.config.language)
                
                # 7. Re-extract quote using LLM
                quote_data = {"quote": None, "confidence": "low", "reasoning": "La trascrizione è vuota."}
                if transcript.strip():
                    item_metadata = media.get("metadata", {})
                    book_title = item_metadata.get("title", "Titolo Sconosciuto")
                    book_author = item_metadata.get("authorName", "Autore Sconosciuto")
                    
                    print(f"Rieseguo estrazione citazione LLM con {self.config.openrouter_llm_model}...")
                    quote_data = self.llm_mgr.extract_verbatim_quote(
                        transcript=transcript,
                        book_title=book_title,
                        author=book_author,
                        bookmark_title=current_title
                    )
                    
                # 8. Overwrite in StoreManager
                success = self.store_mgr.overwrite_quote_data(
                    library_item_id=library_item_id,
                    created_at=created_at,
                    transcript=transcript,
                    quote_data=quote_data,
                    pre_seconds=new_pre,
                    post_seconds=new_post
                )
                
                if not success:
                    print(f"[Errore] Sovrascrittura nello store fallita.")
                    return None
                    
                # 9. Update state in StateManager
                dummy_bookmark = {
                    "libraryItemId": library_item_id,
                    "time": current_time,
                    "title": current_title,
                    "createdAt": created_at
                }
                self.state_mgr.mark_processed(
                    bookmark=dummy_bookmark,
                    status="ok",
                    pre_seconds=new_pre,
                    post_seconds=new_post
                )
                self.state_mgr.save_state()
                
                print(f"[Completato] Citazione rielaborata con successo.")
                
                # Return updated representation
                return self.store_mgr.get_single_quote(library_item_id, created_at)
                
            finally:
                # 10. Clean up audio resource
                if audio_file_path and audio_file_path.exists():
                    try:
                        Path(audio_file_path).unlink()
                    except OSError:
                        pass

    def _poll_youtube_sheet(self) -> None:
        """Reads pending YouTube links from Google Sheet and processes them."""
        print("Polling Google Sheet per nuovi link YouTube...")
        try:
            all_links = self.yt_sheet_client.fetch_all_links()
        except Exception as e:
            print(f"Errore durante la lettura del Google Sheet: {e}")
            return

        pending = [
            link for link in all_links
            if not self.state_mgr.is_youtube_link_processed(link["video_id"], link["timestamp"])
        ]

        if not pending:
            print("Nessun nuovo link YouTube da elaborare.")
            return

        print(f"Rilevati {len(pending)} nuovi link YouTube da elaborare.")
        for link_data in pending:
            self._process_youtube_link_with_retry(link_data)

    def _process_youtube_link_with_retry(self, link_data: Dict[str, Any], max_retries: int = 2) -> None:
        """Attempts to process a YouTube link with retry logic."""
        video_id = link_data["video_id"]
        timestamp = link_data["timestamp"]
        raw_url = link_data["raw_url"]

        print(f"\n[YouTube] Elaborazione video {video_id} al timestamp {timestamp}s...")

        for attempt in range(1, max_retries + 1):
            try:
                self._execute_youtube_pipeline(link_data)
                self.state_mgr.mark_youtube_link_processed(video_id, timestamp, raw_url, "ok")
                self.state_mgr.save_state()
                print(f"[YouTube Completato] Video {video_id}:{timestamp}s salvato con successo.")
                return
            except Exception as e:
                print(f"[YouTube] Tentativo {attempt}/{max_retries} fallito: {e}")
                if attempt < max_retries:
                    time.sleep(2.0)

        # All retries failed — mark as failed to avoid infinite retries
        self.state_mgr.mark_youtube_link_processed(video_id, timestamp, raw_url, "failed", str(e))
        self.state_mgr.save_state()
        print(f"[YouTube Fallito] Video {video_id}:{timestamp}s non elaborato.")

    def _execute_youtube_pipeline(self, link_data: Dict[str, Any]) -> None:
        """Executes the full YouTube extraction pipeline for a single link."""
        video_id = link_data["video_id"]
        timestamp = link_data["timestamp"]
        raw_url = link_data["raw_url"]

        # Build video URL for the store
        video_url = f"https://www.youtube.com/watch?v={video_id}&t={timestamp}"

        # 1. Fetch real video title and channel/author name
        metadata = self.yt_transcript_mgr.get_video_metadata(video_id)
        video_title = metadata.get("title", f"YouTube: {video_id}")
        channel_name = metadata.get("author", "YouTube")

        # 2. Download subtitles
        result = self.yt_transcript_mgr.get_transcript_window(video_id, timestamp)
        transcript = result.get("transcript")
        subtitles_available = result.get("available", False)

        # 3. Extract quote (or create placeholder for manual entry)
        if transcript and transcript.strip():
            print(f"[YouTube] Sottotitoli disponibili per '{video_title}'. Estrazione citazione con LLM...")
            quote_data = self.llm_mgr.extract_youtube_quote(
                transcript=transcript,
                video_title=video_title,
                channel_name=channel_name,
                timestamp=timestamp
            )
        else:
            error_reason = result.get("error_message", "Subtitles not available.")
            print(f"[YouTube] Sottotitoli non disponibili per '{video_title}': {error_reason}")
            quote_data = {
                "quote": None,
                "quote_original": None,
                "quote_language": "",
                "confidence": "low",
                "reasoning": f"Subtitles not available for this video. "
                             f"Please add the quote manually via Verify. ({error_reason})"
            }

        # 4. Save to store
        self.store_mgr.append_youtube_quote(
            video_id=video_id,
            video_title=video_title,
            channel_name=channel_name,
            video_url=video_url,
            timestamp=timestamp,
            transcript=transcript or "",
            quote_data=quote_data,
            pre_seconds=self.config.youtube_pre_seconds,
            post_seconds=self.config.youtube_post_seconds
        )

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
    if config.youtube_enabled:
        print(f"YouTube integration: ENABLED (Sheet ID: {config.youtube_sheet_id[:8]}...)")
    else:
        print("YouTube integration: DISABLED (no API key or Sheet ID configured)")
    
    # Avvio del ciclo di polling in un thread in background (daemon)
    def poll_worker() -> None:
        print("Thread di polling in background avviato.")
        try:
            while True:
                coordinator.run_single_poll()
                time.sleep(config.poll_interval_seconds)
        except Exception as pe:
            print(f"Errore grave nel thread di polling: {pe}")
            traceback.print_exc()

    polling_thread = threading.Thread(target=poll_worker, daemon=True)
    polling_thread.start()
    
    # Inizializzazione e avvio del server Web FastAPI sul thread principale
    web_server = WebServer(coordinator)
    print("Avvio del server Web sulla porta 7777...")
    try:
        uvicorn.run(web_server.app, host="0.0.0.0", port=7777)
    except KeyboardInterrupt:
        print("\nServizio interrotto dall'utente. Spegnimento in corso...")
    finally:
        coordinator.close()
        print("Arrivederci!")

if __name__ == "__main__":
    main()
