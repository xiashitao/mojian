"""Settings: read from .env file."""
import secrets
from pathlib import Path
from pydantic_settings import BaseSettings

# web/ directory
WEB_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # Default LLM provider (DeepSeek). Any OpenAI-compatible service works by
    # overriding the llm_* fields below — no code change needed.
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    # Provider-agnostic gateway overrides; empty -> fall back to deepseek_*.
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""

    # Cheap/fast tier for mechanical tasks (routing extraction, follow-up
    # questions). Empty -> falls back to deepseek_*, then to the main provider.
    fast_llm_base_url: str = ""
    fast_llm_api_key: str = ""
    fast_llm_model: str = ""

    database_path: str = "charts.db"

    jwt_secret: str = secrets.token_hex(32)
    jwt_algorithm: str = "HS256"
    jwt_expire_days: int = 30
    cookie_secure: bool = True  # set False in local dev (.env: COOKIE_SECURE=false)

    # 邮箱验证码登录（OTP）
    email_provider: str = "log"  # log(开发：打印到日志) | smtp(生产)
    email_from: str = "Kairos <noreply@example.com>"
    otp_ttl_seconds: int = 600  # 验证码有效期（默认 10 分钟）
    otp_resend_seconds: int = 60  # 同一邮箱重发冷却
    otp_max_attempts: int = 5  # 单个码最多验证次数
    # SMTP（email_provider=smtp 时用；腾讯云邮件推送提供 SMTP 接入）
    smtp_host: str = ""
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_ssl: bool = True

    class Config:
        env_file = str(WEB_DIR / ".env")
        env_file_encoding = "utf-8"


settings = Settings()

# Resolve database path to absolute
DB_PATH = WEB_DIR / settings.database_path
