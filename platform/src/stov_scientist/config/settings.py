"""Central runtime settings (Pydantic Settings).

Single source of truth for model names, timeouts, retries, temperature and
streaming. Agent code must never hard-code model names or client options.

Environment file: platform/.env (never committed).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PLATFORM_ROOT = Path(__file__).resolve().parents[3]  # platform/


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PLATFORM_ROOT / ".env",
        env_file_encoding="utf-8",
        env_prefix="STOV_",
        case_sensitive=False,
        extra="ignore",
    )

    # --- DeepSeek runtime -------------------------------------------------
    # Spec .env.example uses the unprefixed DEEPSEEK_API_KEY; AliasChoices
    # accepts both that and the STOV_-prefixed form.
    deepseek_api_key: SecretStr | None = Field(
        default=None,
        description="DEEPSEEK_API_KEY",
        validation_alias=AliasChoices("DEEPSEEK_API_KEY", "STOV_DEEPSEEK_API_KEY"),
    )
    main_model: str = Field(default="deepseek-v4-pro", description="complex reasoning model")
    fast_model: str = Field(default="deepseek-v4-flash", description="extraction/classification model")

    # --- LLM behaviour (managed here, not in agent code) ------------------
    llm_timeout: float = 180.0
    llm_max_retries: int = 2
    llm_temperature: float = 0.0
    llm_streaming: bool = True

    # --- LangSmith --------------------------------------------------------
    langsmith_tracing: bool = False
    langsmith_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("LANGSMITH_API_KEY", "STOV_LANGSMITH_API_KEY"),
    )
    langsmith_project: str = "stov-ai-scientist"

    # --- Environment ------------------------------------------------------
    env: str = "development"
    artifact_root: Path = Field(default=PLATFORM_ROOT / ".." / "artifacts")
    database_url: str = ""  # empty -> default local SQLite metadata file
    log_level: str = "INFO"

    # --- Deep Agent behaviour ---------------------------------------------
    structured_output_max_retries: int = Field(
        default=1, description="spec §34: retry once, then STRUCTURED_OUTPUT_FAILURE"
    )

    @property
    def deepseek_available(self) -> bool:
        return self.deepseek_api_key is not None and bool(
            self.deepseek_api_key.get_secret_value().strip()
        )

    @property
    def langsmith_available(self) -> bool:
        return self.langsmith_api_key is not None and bool(
            self.langsmith_api_key.get_secret_value().strip()
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    """Test helper: drop the cached Settings instance."""
    get_settings.cache_clear()
