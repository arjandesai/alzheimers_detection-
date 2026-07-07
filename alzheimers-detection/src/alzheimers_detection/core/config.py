"""Application configuration.

All tunables live here and are overridable via environment variables
(twelve-factor style) so the same image runs in dev/CI/prod without code
changes. Nothing in this file should contain secrets -- those come from
the environment / a secrets manager, never from source.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ALZDX_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- General ---
    app_name: str = "alzheimers-detection"
    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")

    # --- Speech pipeline ---
    asr_backend: str = Field(
        default="faster_whisper",
        description="Which ASR engine implementation to instantiate. "
        "See speech/transcription.py for the registry of valid names.",
    )
    asr_model_size: str = Field(
        default="base",
        description="Model size/checkpoint name, meaning depends on asr_backend.",
    )
    max_audio_duration_seconds: int = Field(
        default=600,
        description="Reject audio longer than this to bound compute cost "
        "and keep inference latency predictable.",
    )
    min_audio_duration_seconds: float = Field(
        default=3.0,
        description="Below this, acoustic features (esp. jitter/shimmer, "
        "pause statistics) are not reliable; flag as insufficient_data.",
    )
    pause_threshold_seconds: float = Field(
        default=0.25,
        description="Gaps between words at or above this duration are "
        "counted as pauses. 250ms is a common threshold in the dementia "
        "speech literature (see docs/DATASETS.md references).",
    )

    # --- Storage / local-first privacy ---
    data_dir: Path = Field(default=Path("./data"))
    keep_uploaded_audio: bool = Field(
        default=False,
        description="If False (default), audio is processed in memory / a "
        "temp file and deleted immediately after feature extraction. "
        "Matches the 'local inference, minimal retention' privacy posture.",
    )

    # --- Database ---
    database_url: str = Field(
        default="postgresql+psycopg://alzdx:alzdx@localhost:5432/alzdx",
        description="SQLAlchemy connection string. Use a sqlite:// URL for "
        "local dev without Docker; production should point at PostgreSQL. "
        "Tests override this via dependency injection, not this setting -- "
        "see tests/conftest.py.",
    )
    db_echo: bool = Field(default=False, description="Log all SQL statements; dev/debug only")

    # --- Auth ---
    jwt_secret_key: str = Field(
        default="CHANGE_ME_dev_only_insecure_default",
        description="HMAC signing key for access tokens. MUST be overridden "
        "via ALZDX_JWT_SECRET_KEY in any non-local environment -- the "
        "default is intentionally insecure so it's obvious in code review "
        "if someone deploys without setting it.",
    )
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_token_expire_minutes: int = Field(default=60)

    # --- API ---
    api_cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor -- import this, not Settings() directly,
    so the whole process shares one instance and env parsing happens once."""
    return Settings()
