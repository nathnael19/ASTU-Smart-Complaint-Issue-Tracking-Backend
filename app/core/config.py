from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App
    APP_NAME: str = "ASTU Smart Complaint & Issue Tracking API"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    # Frontend base URL (for password reset and invite redirects). No trailing slash.
    FRONTEND_URL: str = "https://astu-smart-complaint-issue-tracking.netlify.app"

    # CORS – stored as a comma-separated string in .env, parsed into a list
    CORS_ORIGINS: Union[List[str], str] = ["https://astu-smart-complaint-issue-tracking.netlify.app", "http://localhost:5173", "http://localhost:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Supabase
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str

    # JWT
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # AI Chatbot via OpenRouter (free tier). Get key at https://openrouter.ai/keys
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "google/gemma-2-9b-it:free"  # or e.g. meta-llama/llama-3.2-3b-instruct:free


settings = Settings()
