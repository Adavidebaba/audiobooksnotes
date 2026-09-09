import time
from pathlib import Path
from typing import Dict, Any, Optional

from src.store import StoreManager
from src.llm import LlmManager
from src.audio import AudioManager
from src.stt import SttManager
from src.abs_client import AbsClientManager
from src.state import StateManager


class QuoteReprocessor:
    """Manager responsible for re-processing audio clips or re-extracting quotes using current LLM prompts."""

    def __init__(
        self,
        store_mgr: StoreManager,
        llm_mgr: LlmManager,
        audio_mgr: AudioManager,
        stt_mgr: SttManager,
        abs_client: AbsClientManager,
        state_mgr: StateManager,
        config: Any
    ) -> None:
        """Initializes the QuoteReprocessor with required service dependencies."""
        self.store_mgr = store_mgr
        self.llm_mgr = llm_mgr
        self.audio_mgr = audio_mgr
        self.stt_mgr = stt_mgr
        self.abs_client = abs_client
        self.state_mgr = state_mgr
        self.config = config

    def re_extract_quote_llm(self, library_item_id: str, created_at: int) -> Optional[Dict[str, Any]]:
        """Re-extracts a quote using the existing transcript and the currently active LLM prompt."""
        print(f"\n=== RI-ESTRAZIONE LLM RICHIESTA: {library_item_id} (createdAt: {created_at}) ===")
        quote = self.store_mgr.get_single_quote(library_item_id, created_at)
        if not quote:
            print("[Errore] Citazione non trovata nello store.")
            return None

        transcript = quote.get("transcript", "")
        if not transcript or not transcript.strip():
            print("[Errore] Trascrizione assente o vuota per questa citazione.")
            return None

        source_type = quote.get("source_type", "audiobook")
        quote_data = self._invoke_llm_for_re_extract(source_type, quote, transcript)

        success = self.store_mgr.update_quote(
            library_item_id=library_item_id,
            created_at=created_at,
            new_quote=quote_data.get("quote") or "",
            new_confidence=quote_data.get("confidence", "low"),
            new_reasoning=quote_data.get("reasoning", "")
        )
        if not success:
            print("[Errore] Impossibile aggiornare la citazione nello store.")
            return None

        print(f"[Completato] Ri-estrazione LLM completata con successo: {quote_data.get('confidence')}")
        return self.store_mgr.get_single_quote(library_item_id, created_at)

    def _invoke_llm_for_re_extract(
        self, 
        source_type: str, 
        quote: Dict[str, Any], 
        transcript: str
    ) -> Dict[str, Any]:
        """Invokes appropriate LLM extraction method depending on whether source is audiobook or YouTube."""
        if source_type == "youtube":
            timestamp = int(quote.get("time", 0))
            if timestamp <= 0:
                return self.llm_mgr.extract_youtube_full_video_insights(
                    transcript=transcript,
                    video_title=quote.get("bookTitle", ""),
                    channel_name=quote.get("bookAuthor", "")
                )
            return self.llm_mgr.extract_youtube_quote(
                transcript=transcript,
                video_title=quote.get("bookTitle", ""),
                channel_name=quote.get("bookAuthor", ""),
                timestamp=timestamp
            )
        return self.llm_mgr.extract_verbatim_quote(
            transcript=transcript,
            book_title=quote.get("bookTitle", ""),
            author=quote.get("bookAuthor", ""),
            bookmark_title=quote.get("title", "")
        )

    def reprocess_single_quote_with_expanded_audio(
        self, 
        library_item_id: str, 
        created_at: int
    ) -> Optional[Dict[str, Any]]:
        """Re-downloads expanded audio (+20%), re-transcribes with Whisper and extracts quote via LLM."""
        print(f"\n=== RIPROCESSO AUDIO CITAZIONE RICHIESTO: {library_item_id} (createdAt: {created_at}) ===")
        current_quote = self.store_mgr.get_single_quote(library_item_id, created_at)
        if not current_quote:
            print("[Errore] Citazione non trovata nello store.")
            return None

        current_time = current_quote.get("time", 0.0)
        current_title = current_quote.get("title", "")
        current_window = current_quote.get("audio_window", {"pre": 30, "post": 30})
        new_pre = int(round(current_window.get("pre", 30) * 1.2))
        new_post = int(round(current_window.get("post", 30) * 1.2))

        try:
            meta = self.abs_client.get_item_metadata(library_item_id)
            media = meta.get("media", {})
            tracks = media.get("tracks", [])
            duration = float(media.get("duration", 0.0))
        except Exception as e:
            print(f"[Errore] Impossibile recuperare metadati da ABS per riprocessare: {e}")
            return None

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
            print(f"Rieseguo trascrizione Whisper per {audio_file_path.name}...")
            transcript = self.stt_mgr.transcribe_audio(audio_file_path, self.config.language)

            quote_data = {"quote": None, "confidence": "low", "reasoning": "La trascrizione è vuota."}
            if transcript.strip():
                item_metadata = media.get("metadata", {})
                quote_data = self.llm_mgr.extract_verbatim_quote(
                    transcript=transcript,
                    book_title=item_metadata.get("title", "Titolo Sconosciuto"),
                    author=item_metadata.get("authorName", "Autore Sconosciuto"),
                    bookmark_title=current_title
                )

            success = self.store_mgr.overwrite_quote_data(
                library_item_id=library_item_id,
                created_at=created_at,
                transcript=transcript,
                quote_data=quote_data,
                pre_seconds=new_pre,
                post_seconds=new_post
            )
            if not success:
                return None

            dummy_bookmark = {
                "libraryItemId": library_item_id,
                "time": current_time,
                "title": current_title,
                "createdAt": created_at
            }
            self.state_mgr.mark_processed(dummy_bookmark, "ok", new_pre, new_post)
            self.state_mgr.save_state()
            return self.store_mgr.get_single_quote(library_item_id, created_at)
        finally:
            if audio_file_path and audio_file_path.exists():
                try:
                    Path(audio_file_path).unlink()
                except OSError:
                    pass
