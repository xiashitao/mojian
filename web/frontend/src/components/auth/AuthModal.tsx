import { useEffect, useState, type FormEvent } from "react";
import { useAuth } from "../../auth";
import { sendEmailCode } from "../../api/authApi";

export interface AuthModalProps {
  onClose: () => void;
  /** Optional guiding line shown at the top (e.g. when chat is gated). */
  prompt?: string;
}

/** 邮箱验证码登录（免密码，两步：输邮箱 → 输验证码）。首次登录自动建号。
 *  复用于顶部账号菜单与"未登录尝试聊天"的登录引导。 */
export function AuthModal({ onClose, prompt }: AuthModalProps) {
  const { loginWithCode } = useAuth();
  const [step, setStep] = useState<"email" | "code">("email");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [cooldown, setCooldown] = useState(0);

  // Esc closes the modal — standard dialog affordance.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  // Resend cooldown ticker.
  useEffect(() => {
    if (cooldown <= 0) return;
    const t = setTimeout(() => setCooldown((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [cooldown]);

  const doSend = async () => {
    setError(null);
    setSubmitting(true);
    try {
      const res = await sendEmailCode(email.trim());
      setStep("code");
      setCooldown(res.resend_after ?? 60);
    } catch (err) {
      setError(err instanceof Error ? err.message : "发送失败，请重试");
    } finally {
      setSubmitting(false);
    }
  };

  const handleEmailSubmit = (e: FormEvent) => {
    e.preventDefault();
    void doSend();
  };

  const handleCodeSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await loginWithCode(email.trim(), code.trim());
      // success triggers a reload; nothing more to do here
    } catch (err) {
      setError(err instanceof Error ? err.message : "验证失败，请重试");
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-scrim" onClick={onClose}>
      <div
        className="auth-modal"
        role="dialog"
        aria-modal="true"
        aria-label={prompt ? "登录以继续" : "邮箱验证码登录"}
        onClick={(e) => e.stopPropagation()}
      >
        {prompt && <p className="auth-modal__prompt">{prompt}</p>}
        <h3 className="auth-modal__title">邮箱验证码登录</h3>

        {step === "email" ? (
          <form className="auth-form" onSubmit={handleEmailSubmit}>
            <input
              className="auth-input"
              type="email"
              placeholder="邮箱"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              // eslint-disable-next-line jsx-a11y/no-autofocus
              autoFocus
              required
            />
            {error && <p className="auth-error">{error}</p>}
            <button
              type="submit"
              className="auth-submit"
              disabled={submitting || !email.trim()}
            >
              {submitting ? "发送中…" : "发送验证码"}
            </button>
          </form>
        ) : (
          <form className="auth-form" onSubmit={handleCodeSubmit}>
            <p className="auth-hint">
              验证码已发送至 <b>{email}</b>
            </p>
            <input
              className="auth-input"
              inputMode="numeric"
              placeholder="6 位验证码"
              value={code}
              onChange={(e) =>
                setCode(e.target.value.replace(/\D/g, "").slice(0, 6))
              }
              autoComplete="one-time-code"
              maxLength={6}
              // eslint-disable-next-line jsx-a11y/no-autofocus
              autoFocus
              required
            />
            {error && <p className="auth-error">{error}</p>}
            <button
              type="submit"
              className="auth-submit"
              disabled={submitting || code.length < 4}
            >
              {submitting ? "登录中…" : "登录"}
            </button>
            <div className="auth-otp-actions">
              <button
                type="button"
                className="auth-linkbtn"
                onClick={() => {
                  setStep("email");
                  setCode("");
                  setError(null);
                }}
              >
                换邮箱
              </button>
              <button
                type="button"
                className="auth-linkbtn"
                disabled={cooldown > 0 || submitting}
                onClick={() => void doSend()}
              >
                {cooldown > 0 ? `重新发送（${cooldown}s）` : "重新发送"}
              </button>
            </div>
          </form>
        )}

        <p className="auth-hint">
          首次用邮箱登录会自动创建账号；登录后当前匿名的对话和记忆会并入你的账号。
        </p>
      </div>
    </div>
  );
}
