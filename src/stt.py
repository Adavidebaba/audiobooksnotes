import base64
from pathlib import Path
import httpx

class SttManager:
    """Manager responsible for transcribing audio files using the OpenRouter Audio API."""

    def __init__(self, api_key: str, model_name: str = "mistralai/voxtral-mini-transcribe") -> None:
        """Initializes the SttManager with OpenRouter credentials and target model."""
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = "https://openrouter.ai/api/v1/audio/transcriptions"

    def transcribe_audio(self, audio_path: Path, language: str = "it") -> str:
        """Transcribes the given audio file using OpenRouter.
        
        Args:
            audio_path: Path to the local MP3 file to transcribe.
            language: The ISO-639-1 language code (defaults to 'it' for Italian).
            
        Returns:
            The raw text transcription.
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        try:
            # Leggi il file audio e codificalo in base64
            with open(audio_path, "rb") as audio_file:
                audio_bytes = audio_file.read()
                base64_audio = base64.b64encode(audio_bytes).decode("utf-8")

            # Determina il formato dall'estensione del file (es. "mp3")
            audio_format = audio_path.suffix.lstrip(".").lower()
            if not audio_format:
                audio_format = "mp3"

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/adavide/audiobooksnotes",
                "X-Title": "AudiobookNotes"
            }

            payload = {
                "model": self.model_name,
                "input_audio": {
                    "data": base64_audio,
                    "format": audio_format
                },
                "language": language
            }

            with httpx.Client(timeout=60.0) as client:
                response = client.post(self.base_url, headers=headers, json=payload)
                response.raise_for_status()
                result = response.json()

            if "text" in result:
                return result["text"].strip()
            elif "choices" in result and len(result["choices"]) > 0:
                choice = result["choices"][0]
                if "text" in choice:
                    return choice["text"].strip()
                elif "message" in choice and "content" in choice["message"]:
                    return choice["message"]["content"].strip()
            
            raise KeyError(f"Formato risposta OpenRouter non previsto: {result}")

        except Exception as e:
            raise RuntimeError(f"OpenRouter STT API call failed: {e}")
            
    def close(self) -> None:
        """Closes the client connections if necessary (standard interface)."""
        pass

