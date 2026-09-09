import json
from openai import OpenAI
from typing import Dict, Any, Optional

from src.prompt_manager import (
    PromptManager,
    DEFAULT_AUDIOBOOKS_SYSTEM_PROMPT,
    DEFAULT_YOUTUBE_SYSTEM_PROMPT,
    DEFAULT_YOUTUBE_FULL_VIDEO_SYSTEM_PROMPT
)

class LlmManager:
    """Manager responsible for extracting verbatim quotes from audio transcriptions using OpenAI Chat API."""

    def __init__(
        self, 
        api_key: str, 
        model_name: str = "openrouter/auto",
        prompt_manager: Optional[PromptManager] = None
    ) -> None:
        """Initializes the LlmManager with OpenRouter credentials, target model, and prompt manager."""
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        )
        self.model_name = model_name
        self.prompt_manager = prompt_manager

    def _get_model_name(self) -> str:
        """Returns the active model name from prompt_manager or fallback."""
        if self.prompt_manager:
            return self.prompt_manager.get_model_name()
        return self.model_name

    def _get_system_prompt(self) -> str:
        """Returns the system instructions for quote extraction."""
        if self.prompt_manager:
            return self.prompt_manager.get_prompt("audiobooks_system_prompt")
        return DEFAULT_AUDIOBOOKS_SYSTEM_PROMPT

    def _get_user_prompt(
        self, 
        transcript: str, 
        book_title: str, 
        author: str, 
        bookmark_title: Optional[str]
    ) -> str:
        """Constructs the user message string with context details."""
        prompt = (
            f"Dettagli Audiolibro:\n"
            f"- Titolo: {book_title}\n"
            f"- Autore: {author}\n\n"
            f"Nota del bookmark inserita dall'utente: '{bookmark_title or ''}'\n\n"
            f"Trascrizione completa dei 60 secondi (il bookmark è al secondo 30, ovvero a metà di questa trascrizione):\n"
            f"\"\"\"\n{transcript}\n\"\"\"\n"
        )
        return prompt

    def extract_verbatim_quote(
        self, 
        transcript: str, 
        book_title: str, 
        author: str, 
        bookmark_title: Optional[str]
    ) -> Dict[str, Any]:
        """Calls the OpenAI Chat API to extract the verbatim quote.
        
        Returns:
            A dictionary containing 'quote' (str or None), 'confidence' (str), and 'reasoning' (str).
        """
        if not transcript.strip():
            return {
                "quote": None,
                "confidence": "low",
                "reasoning": "La trascrizione è vuota."
            }

        try:
            response = self.client.chat.completions.create(
                model=self._get_model_name(),
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": self._get_user_prompt(transcript, book_title, author, bookmark_title)}
                ],
                temperature=0.2
            )
            
            result_text = response.choices[0].message.content
            return json.loads(result_text)
            
        except Exception as e:
            # Fallback in case of API failure or parsing errors
            return {
                "quote": None,
                "confidence": "low",
                "reasoning": f"Errore nell'estrazione LLM: {str(e)}"
            }

    def _get_youtube_system_prompt(self) -> str:
        """Returns the system instructions for YouTube quote extraction with translation."""
        if self.prompt_manager:
            return self.prompt_manager.get_prompt("youtube_system_prompt")
        return DEFAULT_YOUTUBE_SYSTEM_PROMPT

    def _get_youtube_user_prompt(
        self,
        transcript: str,
        video_title: str,
        channel_name: str,
        timestamp: int
    ) -> str:
        """Constructs the user message for YouTube quote extraction."""
        minutes = timestamp // 60
        seconds = timestamp % 60
        return (
            f"Dettagli Video YouTube:\n"
            f"- Titolo: {video_title}\n"
            f"- Canale: {channel_name}\n"
            f"- Timestamp condiviso: {minutes}m {seconds}s\n\n"
            f"Trascrizione dei sottotitoli nella finestra temporale "
            f"(il timestamp è circa a metà di questa trascrizione):\n"
            f"\"\"\"\n{transcript}\n\"\"\"\n"
        )

    def extract_youtube_quote(
        self,
        transcript: str,
        video_title: str,
        channel_name: str,
        timestamp: int
    ) -> Dict[str, Any]:
        """Calls the OpenAI Chat API to extract a quote from YouTube subtitles.

        Returns:
            A dictionary containing 'quote', 'confidence', and 'reasoning'.
        """
        if not transcript or not transcript.strip():
            return {
                "quote": None,
                "confidence": "low",
                "reasoning": "La trascrizione è vuota."
            }

        try:
            response = self.client.chat.completions.create(
                model=self._get_model_name(),
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": self._get_youtube_system_prompt()},
                    {"role": "user", "content": self._get_youtube_user_prompt(
                        transcript, video_title, channel_name, timestamp
                    )}
                ],
                temperature=0.2
            )

            result_text = response.choices[0].message.content
            parsed = json.loads(result_text)
            return {
                "quote": parsed.get("quote"),
                "confidence": parsed.get("confidence", "high"),
                "reasoning": parsed.get("reasoning", "")
            }

        except Exception as e:
            return {
                "quote": None,
                "confidence": "low",
                "reasoning": f"Errore nell'estrazione LLM YouTube: {str(e)}"
            }

    def _get_youtube_full_video_system_prompt(self) -> str:
        """Returns the system instructions for extracting core insights via a verbatim super-cut montage."""
        if self.prompt_manager:
            return self.prompt_manager.get_prompt("youtube_full_video_system_prompt")
        return DEFAULT_YOUTUBE_FULL_VIDEO_SYSTEM_PROMPT

    def _get_youtube_full_video_user_prompt(
        self,
        transcript: str,
        video_title: str,
        channel_name: str
    ) -> str:
        """Constructs the user message for full YouTube video insight extraction."""
        # Safety cap at 150k characters (~35k tokens, ~2-3 hours of speech)
        capped_transcript = transcript[:150000]
        if len(transcript) > 150000:
            capped_transcript += "\n[...Trascrizione troncata per limiti di sicurezza...]"

        return (
            f"Dettagli Video YouTube (Intero Video):\n"
            f"- Titolo: {video_title}\n"
            f"- Canale: {channel_name}\n\n"
            f"Trascrizione integrale dei sottotitoli del video:\n"
            f"\"\"\"\n{capped_transcript}\n\"\"\"\n"
        )

    def extract_youtube_full_video_insights(
        self,
        transcript: str,
        video_title: str,
        channel_name: str
    ) -> Dict[str, Any]:
        """Calls the OpenAI Chat API to extract full video insights and core lessons.

        Returns:
            A dictionary containing 'quote', 'confidence', and 'reasoning'.
        """
        if not transcript or not transcript.strip():
            return {
                "quote": None,
                "confidence": "low",
                "reasoning": "La trascrizione del video è vuota."
            }

        try:
            response = self.client.chat.completions.create(
                model=self._get_model_name(),
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": self._get_youtube_full_video_system_prompt()},
                    {"role": "user", "content": self._get_youtube_full_video_user_prompt(
                        transcript, video_title, channel_name
                    )}
                ],
                temperature=0.2
            )

            result_text = response.choices[0].message.content
            parsed = json.loads(result_text)
            return {
                "quote": parsed.get("quote"),
                "confidence": parsed.get("confidence", "high"),
                "reasoning": parsed.get("reasoning", "")
            }

        except Exception as e:
            return {
                "quote": None,
                "confidence": "low",
                "reasoning": f"Errore nell'estrazione LLM degli insight del video: {str(e)}"
            }



