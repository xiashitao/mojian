"""Settings: read from .env file."""
from pathlib import Path
from pydantic_settings import BaseSettings

# web/ directory
WEB_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    database_path: str = "charts.db"

    class Config:
        env_file = str(WEB_DIR / ".env")
        env_file_encoding = "utf-8"


settings = Settings()

# Resolve database path to absolute
DB_PATH = WEB_DIR / settings.database_path
