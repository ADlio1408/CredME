"""
Centralized config, loaded from environment variables only.

No secret ever has a default value baked into code - if an operator
forgets to set API_KEY, the app should fail closed (see security.py),
not silently accept an empty/hardcoded credential.
"""
import os

from dotenv import load_dotenv

load_dotenv()  # loads .env for local dev; in real deployments, use the platform's secret manager


class Settings:
    api_key: str | None = os.environ.get("CREDIT_INTEL_API_KEY")
    database_url: str = os.environ.get("DATABASE_URL", "sqlite:///./credit_intel.db")
    anthropic_api_key: str | None = os.environ.get("ANTHROPIC_API_KEY")
    cors_origins: list[str] = os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")
    env: str = os.environ.get("APP_ENV", "development")


settings = Settings()
