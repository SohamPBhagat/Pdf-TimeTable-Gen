"""Configuration — env vars / CLI args for LLM endpoint, key, model."""

import os
from dataclasses import dataclass, field


@dataclass
class LLMConfig:
    """Configuration for the optional AI Analyzer."""

    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-4o"
    max_tokens: int = 1024
    temperature: float = 0.3

    @classmethod
    def from_env(cls) -> "LLMConfig":
        return cls(
            base_url=os.environ.get("LLM_BASE_URL", cls.base_url),
            api_key=os.environ.get("LLM_API_KEY", ""),
            model=os.environ.get("LLM_MODEL", cls.model),
            max_tokens=int(os.environ.get("LLM_MAX_TOKENS", cls.max_tokens)),
            temperature=float(os.environ.get("LLM_TEMPERATURE", cls.temperature)),
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)


@dataclass
class Settings:
    """Application settings."""

    llm: LLMConfig = field(default_factory=LLMConfig.from_env)
    default_output_dir: str = "."


settings = Settings()
