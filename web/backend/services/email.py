"""事务邮件——发送登录验证码。

开发期（email_provider=log）把验证码打到后端日志，本地不配任何邮箱也能跑通
全流程；生产期（email_provider=smtp）走 SMTP，腾讯云邮件推送 / 阿里云 / 任意
SMTP 都通用，换供应商只改 .env、不动代码。
"""
from __future__ import annotations

import logging
import smtplib
import ssl
from email.mime.text import MIMEText
from email.utils import parseaddr

from ..config import settings

logger = logging.getLogger("kairos.email")


def send_login_code(to_email: str, code: str) -> None:
    """把登录验证码发到 `to_email`。发送方式由 settings.email_provider 决定。"""
    minutes = max(1, settings.otp_ttl_seconds // 60)
    subject = "Kairos 登录验证码"
    body = (
        f"你的 Kairos 登录验证码是：{code}\n\n"
        f"{minutes} 分钟内有效。若非本人操作，请忽略此邮件。"
    )

    if settings.email_provider == "smtp":
        _send_smtp(to_email, subject, body)
    else:
        # 开发/日志模式：验证码直接进后端日志，本地就能拿到码继续验证。
        logger.warning("[email:log] to=%s 登录验证码=%s", to_email, code)


def _send_smtp(to_email: str, subject: str, body: str) -> None:
    from_addr = parseaddr(settings.email_from)[1] or settings.smtp_user
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = settings.email_from
    msg["To"] = to_email

    if settings.smtp_ssl:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(
            settings.smtp_host, settings.smtp_port, context=ctx, timeout=15
        ) as s:
            s.login(settings.smtp_user, settings.smtp_password)
            s.sendmail(from_addr, [to_email], msg.as_string())
    else:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as s:
            s.starttls(context=ssl.create_default_context())
            s.login(settings.smtp_user, settings.smtp_password)
            s.sendmail(from_addr, [to_email], msg.as_string())
