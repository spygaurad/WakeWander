from pydantic_settings import BaseSettings
from functools import lru_cache
from pydantic import Field, AliasChoices, field_validator
import os
from dotenv import load_dotenv

load_dotenv()

cors_origins: list[str] = os.getenv("CORS_ORIGINS", "").split(",")

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/travel_planner"
        # optional, for using OpenAI or Gemini APIs
    OPENAI_API_KEY: str | None = None

    # accept either GOOGLE_API_KEY or GEMINI_API_KEY
    GOOGLE_API_KEY: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GOOGLE_API_KEY", "GEMINI_API_KEY")
    )

    CORS_ORIGINS: list[str] = cors_origins

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
