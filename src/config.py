import os
from pathlib import Path
from dotenv import load_dotenv

class ConfigManager:
    """Manages the configuration loading, validation, and typed access to env variables."""
    
    def __init__(self, env_path: str = None) -> None:
        """Initializes ConfigManager, loads .env file if path is provided or from default location."""
        if env_path:
            load_dotenv(dotenv_path=env_path)
        else:
            load_dotenv()
        self._validate_and_load()

    def _validate_and_load(self) -> None:
        """Validates crucial settings and populates local instance properties."""
        self.abs_url = os.getenv("ABS_URL", "").rstrip("/")
        self.abs_token = os.getenv("ABS_TOKEN", "")
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "")
        
        # Verify required settings
        if not self.abs_url:
            raise ValueError("ABS_URL is required in environment/dotenv")
        if not self.abs_token:
            raise ValueError("ABS_TOKEN is required in environment/dotenv")
        if not self.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY is required in environment/dotenv")

        # Models
        self.openrouter_stt_model = os.getenv("OPENROUTER_STT_MODEL", "mistralai/voxtral-mini-transcribe")
        self.openrouter_llm_model = os.getenv("OPENROUTER_LLM_MODEL", "openrouter/auto")

        # Application parameters
        self.poll_interval_seconds = int(os.getenv("POLL_INTERVAL_SECONDS", "60"))
        self.pre_seconds = int(os.getenv("PRE_SECONDS", "30"))
        self.post_seconds = int(os.getenv("POST_SECONDS", "30"))
        self.language = os.getenv("LANGUAGE", "it")
        self.data_dir = Path(os.getenv("DATA_DIR", "./data"))
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        
        # Bootstrap options
        self.bootstrap_mode = os.getenv("BOOTSTRAP_MODE", "skip")
        self.bootstrap_since_iso = os.getenv("BOOTSTRAP_SINCE_ISO", "")

        # YouTube via Google Sheets (optional)
        self.google_sheets_api_key = os.getenv("GOOGLE_SHEETS_API_KEY", "")
        self.youtube_sheet_id = os.getenv("YOUTUBE_SHEET_ID", "")
        self.youtube_pre_seconds = int(os.getenv("YOUTUBE_PRE_SECONDS", "60"))
        self.youtube_post_seconds = int(os.getenv("YOUTUBE_POST_SECONDS", "60"))
        self.youtube_enabled = bool(self.google_sheets_api_key and self.youtube_sheet_id)

        # Create directories if they do not exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.books_dir = self.data_dir / "books"
        self.books_dir.mkdir(parents=True, exist_ok=True)
        self.state_file_path = self.data_dir / "state.json"
