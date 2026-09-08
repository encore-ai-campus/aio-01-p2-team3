"""baby_info_server configuration."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    pediatric_api_key: str = ""
    emergency_api_key: str = ""
    pediatric_api_url: str = ""
    emergency_api_url: str = ""
    external_api_timeout_seconds: int = Field(default=5, ge=1, le=30)
    mcp_host: str = "127.0.0.1"
    mcp_port: int = Field(default=8102, ge=1, le=65535)
    postgres_dsn: str = ""
    ollama_base_url: str = "http://localhost:11434"
    ollama_embedding_model: str = "nomic-embed-text"
    ollama_embedding_dimension: int = Field(default=768, ge=1)
    ollama_timeout_seconds: int = Field(default=30, ge=1, le=120)
    rag_top_k: int = Field(default=5, ge=1, le=10)
    rag_min_similarity: float = Field(default=0.70, ge=0, le=1)
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
