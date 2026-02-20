"""
Application configuration settings.
"""
from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True

    # LLM Provider Configuration
    default_llm_provider: Literal["openai", "anthropic", "together", "ollama"] = "openai"

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4-turbo-preview"
    openai_temperature: float = 0.7

    # Anthropic
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-sonnet-20241022"
    anthropic_temperature: float = 0.7

    # Together AI
    together_api_key: str = ""
    together_model: str = "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"
    together_temperature: float = 0.7

    # Ollama (Local)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    ollama_temperature: float = 0.7

    # Content Policy
    default_content_policy: Literal["defensive", "educational", "advanced", "unrestricted"] = "educational"

    # Session Configuration
    session_timeout: int = 3600
    max_context_length: int = 4000

    # Authentication
    require_auth: bool = False
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # Storage Paths
    scenarios_path: str = "./scenarios/generated"
    data_path: str = "./data"

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
