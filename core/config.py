from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    CHAT_TTL: int = 3600
    MAX_MESSAGES: int = 12
    LLM_MODEL: str = "gpt-4.1-mini"
    OPENAI_API_KEY: str
    REDIS_PASS: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
