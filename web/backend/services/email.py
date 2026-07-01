"""事务邮件——发送登录验证码。

三种发送方式，换供应商/方式只改 .env、不动代码：
- log     开发：验证码打到后端日志，本地不配任何邮箱也能跑通全流程。
- smtp    通用 SMTP（老/企业账号的腾讯云、阿里云等）。
- tencent 腾讯云邮件推送 API（SendEmail，模板发信）。2026-03-02 起腾讯云对
          新开通的个人实名用户关闭了 SMTP，个人新账号只能走这条。
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import smtplib
import ssl
import time
import urllib.request
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

    if settings.email_provider == "tencent":
        _send_tencent(to_email, code, subject)
    elif settings.email_provider == "smtp":
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


# ── 腾讯云邮件推送 SendEmail（模板发信 + TC3-HMAC-SHA256 签名）─────────────
# 文档：https://cloud.tencent.com/document/product/1288/51034
_SES_HOST = "ses.tencentcloudapi.com"
_SES_SERVICE = "ses"
_SES_ACTION = "SendEmail"
_SES_VERSION = "2020-10-02"


def _send_tencent(to_email: str, code: str, subject: str) -> None:
    """走腾讯云邮件推送 API 发验证码。正文由控制台里审核通过的模板决定，
    模板里放变量 {{code}}，这里通过 TemplateData 把真实验证码填进去。"""
    if not (settings.tencent_secret_id and settings.tencent_secret_key
            and settings.tencent_template_id):
        raise RuntimeError(
            "腾讯云发信未配置：需要 TENCENT_SECRET_ID / TENCENT_SECRET_KEY / "
            "TENCENT_TEMPLATE_ID（.env）"
        )

    payload = {
        "FromEmailAddress": settings.email_from,
        "Destination": [to_email],
        "Subject": subject,
        "Template": {
            "TemplateID": settings.tencent_template_id,
            "TemplateData": json.dumps({"code": code}, ensure_ascii=False),
        },
        "TriggerType": 1,  # 1=触发类（验证码/通知），别归到营销类
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = _tc3_headers(body)

    req = urllib.request.Request(
        f"https://{_SES_HOST}/", data=body, headers=headers, method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw = resp.read().decode("utf-8")
    data = json.loads(raw).get("Response", {})
    if "Error" in data:
        err = data["Error"]
        raise RuntimeError(
            f"腾讯云发信失败：{err.get('Code')} {err.get('Message')}"
        )
    logger.info("[email:tencent] to=%s MessageId=%s", to_email, data.get("MessageId"))


def _tc3_headers(body: bytes) -> dict[str, str]:
    """构造腾讯云 TC3-HMAC-SHA256 签名所需的请求头。"""
    secret_id = settings.tencent_secret_id
    secret_key = settings.tencent_secret_key
    region = settings.tencent_ses_region
    ct = "application/json; charset=utf-8"
    timestamp = int(time.time())
    date = time.strftime("%Y-%m-%d", time.gmtime(timestamp))

    # 1) 规范请求串
    canonical_headers = (
        f"content-type:{ct}\n"
        f"host:{_SES_HOST}\n"
        f"x-tc-action:{_SES_ACTION.lower()}\n"
    )
    signed_headers = "content-type;host;x-tc-action"
    hashed_payload = hashlib.sha256(body).hexdigest()
    canonical_request = "\n".join(
        ["POST", "/", "", canonical_headers, signed_headers, hashed_payload]
    )

    # 2) 待签名字符串
    scope = f"{date}/{_SES_SERVICE}/tc3_request"
    hashed_canonical = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
    string_to_sign = "\n".join(
        ["TC3-HMAC-SHA256", str(timestamp), scope, hashed_canonical]
    )

    # 3) 逐级派生签名密钥
    def _hmac(key: bytes, msg: str) -> bytes:
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

    secret_date = _hmac(("TC3" + secret_key).encode("utf-8"), date)
    secret_service = _hmac(secret_date, _SES_SERVICE)
    secret_signing = _hmac(secret_service, "tc3_request")
    signature = hmac.new(
        secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    authorization = (
        f"TC3-HMAC-SHA256 Credential={secret_id}/{scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )
    return {
        "Authorization": authorization,
        "Content-Type": ct,
        "Host": _SES_HOST,
        "X-TC-Action": _SES_ACTION,
        "X-TC-Version": _SES_VERSION,
        "X-TC-Region": region,
        "X-TC-Timestamp": str(timestamp),
    }
