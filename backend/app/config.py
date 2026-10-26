import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./interview_prep.db"
    JWT_SECRET: str = "4f63c87e83dbbfa20d6f45c85023901b0b5cd30a3f9e8a719c8f8b89d4d5e6a1"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 11520
    GEMINI_API_KEY: str = ""
    DEMO_MODE: bool = True
    PORT: int = 8000
    HOST: str = "127.0.0.1"

    class Config:
        env_file = ".env"
        extra = "ignore"

    @property
    def clean_database_url(self) -> str:
        # standard sqlalchemy fix for postgres URL format change
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        # On Vercel / serverless, local directory is read-only. Fallback to /tmp for sqlite
        if os.getenv("VERCEL") and url.startswith("sqlite:///."):
            url = "sqlite:////tmp/interview_prep.db"
        return url

settings = Settings()
