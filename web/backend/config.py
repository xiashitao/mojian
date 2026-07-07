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
    # log(开发：打印到日志) | smtp(通用 SMTP) | tencent(腾讯云邮件推送 API)
    # 注意：2026-03-02 起腾讯云对新开通的个人实名用户关闭 SMTP，只能走 tencent(API)。
    email_provider: str = "log"
    email_from: str = "Kairos <noreply@example.com>"
    otp_ttl_seconds: int = 600  # 验证码有效期（默认 10 分钟）
    otp_resend_seconds: int = 60  # 同一邮箱重发冷却
    otp_max_attempts: int = 5  # 单个码最多验证次数
    # SMTP（email_provider=smtp 时用；老账号/企业账号的腾讯云可走 SMTP）
    smtp_host: str = ""
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_ssl: bool = True
    # 腾讯云邮件推送 API（email_provider=tencent 时用）。个人新账号只能走这条。
    tencent_secret_id: str = ""  # 访问管理(CAM)里的 SecretId
    tencent_secret_key: str = ""  # 对应 SecretKey（机密，只填服务器 .env）
    tencent_ses_region: str = "ap-guangzhou"  # ap-guangzhou | ap-hongkong
    tencent_template_id: int = 0  # 审核通过的邮件模板 ID（正文含 {{code}}）

    # Google 登录（OAuth 2.0）。留空则前端不显示 Google 按钮。
    google_client_id: str = ""
    google_client_secret: str = ""
    # 站点公网地址，用于拼 OAuth 回调地址与登录后跳转。留空则按请求地址推断
    # （生产建议显式填，如 https://kairos.xsticq.com，与 Google 后台登记的一致）。
    public_base_url: str = ""

    # 用户画像:每 N 轮咨询后用 fast 模型批量更新一次(profile_enabled=False 可一键关闭)。
    profile_enabled: bool = True
    profile_update_interval: int = 3  # 每 N 轮触发一次更新

    # 火山引擎大模型 ASR(语音输入)。两种鉴权填其一,新版优先;
    # 都不填则 /api/asr/enabled 返回 false,前端不显示麦克风按钮。
    volc_asr_api_key: str = ""  # 新版控制台:单个 API Key
    volc_asr_app_id: str = ""  # 旧版控制台:App ID
    volc_asr_access_token: str = ""  # 旧版控制台:Access Token

    class Config:
        env_file = str(WEB_DIR / ".env")
        env_file_encoding = "utf-8"


settings = Settings()

# Resolve database path to absolute
DB_PATH = WEB_DIR / settings.database_path
