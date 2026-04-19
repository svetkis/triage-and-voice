from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    llm_timeout_seconds: float = 60.0
    llm_max_retries: int = 3
    llm_seed: int = 42
    expose_trace: bool = False
    model_config = {"env_file": ".env"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
