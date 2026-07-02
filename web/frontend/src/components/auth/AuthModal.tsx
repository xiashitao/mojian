import { useEffect, useState, type FormEvent } from "react";
import { useAuth } from "../../auth";
import { fetchProviders, sendEmailCode, startGoogleLogin } from "../../api/authApi";

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
  const [googleEnabled, setGoogleEnabled] = useState(false);

  // Only offer Google if the server has it configured.
  useEffect(() => {
    fetchProviders().then((p) => setGoogleEnabled(p.google));
  }, []);

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

        {step === "email" && googleEnabled && (
          <>
            <div className="auth-divider">
              <span>或</span>
            </div>
            <button
              type="button"
              className="auth-google"
              onClick={() => startGoogleLogin()}
            >
              <svg className="auth-google__icon" viewBox="0 0 18 18" aria-hidden="true">
                <path fill="#4285F4" d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.92c1.7-1.57 2.68-3.88 2.68-6.62z" />
                <path fill="#34A853" d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.92-2.26c-.8.54-1.84.86-3.04.86-2.34 0-4.32-1.58-5.03-3.7H.96v2.33A9 9 0 0 0 9 18z" />
                <path fill="#FBBC05" d="M3.97 10.72a5.4 5.4 0 0 1 0-3.44V4.95H.96a9 9 0 0 0 0 8.1l3.01-2.33z" />
                <path fill="#EA4335" d="M9 3.58c1.32 0 2.5.45 3.44 1.35l2.58-2.58C13.47.89 11.43 0 9 0A9 9 0 0 0 .96 4.95l3.01 2.33C4.68 5.16 6.66 3.58 9 3.58z" />
              </svg>
              使用 Google 登录
            </button>
          </>
        )}

        <p className="auth-hint">
          首次用邮箱登录会自动创建账号；登录后当前匿名的对话和记忆会并入你的账号。
        </p>
      </div>
    </div>
  );
}
