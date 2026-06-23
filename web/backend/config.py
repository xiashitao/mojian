"""Settings: read from .env file."""
import secrets
from pathlib import Path
from pydantic_settings import BaseSettings

# web/ directory
WEB_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    database_path: str = "charts.db"

    jwt_secret: str = secrets.token_hex(32)
    jwt_algorithm: str = "HS256"
    jwt_expire_days: int = 30
    cookie_secure: bool = True  # set False in local dev (.env: COOKIE_SECURE=false)

    class Config:
        env_file = str(WEB_DIR / ".env")
        env_file_encoding = "utf-8"


settings = Settings()

# Resolve database path to absolute
DB_PATH = WEB_DIR / settings.database_path
