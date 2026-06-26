import { useEffect, useState, type FormEvent } from "react";
import { useAuth } from "../../auth";

type Mode = "login" | "register";

export interface AuthModalProps {
  onClose: () => void;
  /** Optional guiding line shown above the tabs (e.g. when chat is gated). */
  prompt?: string;
}

/** Login / register modal. Reused by the header account menu and the
 *  login-gate that fires when a signed-out user tries to chat. */
export function AuthModal({ onClose, prompt }: AuthModalProps) {
  const { login, register } = useAuth();
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Esc closes the modal — standard dialog affordance.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (mode === "login") await login(email, password);
      else await register(email, password, name);
      // success triggers a reload; nothing more to do here
    } catch (err) {
      setError(err instanceof Error ? err.message : "出错了，请重试");
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-scrim" onClick={onClose}>
      <div
        className="auth-modal"
        role="dialog"
        aria-modal="true"
        aria-label={prompt ? "登录以继续" : "登录或注册"}
        onClick={(e) => e.stopPropagation()}
      >
        {prompt && <p className="auth-modal__prompt">{prompt}</p>}

        <div className="auth-modal__tabs">
          <button
            type="button"
            className={`auth-modal__tab ${mode === "login" ? "is-active" : ""}`}
            onClick={() => setMode("login")}
          >
            登录
          </button>
          <button
            type="button"
            className={`auth-modal__tab ${mode === "register" ? "is-active" : ""}`}
            onClick={() => setMode("register")}
          >
            注册
          </button>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          {mode === "register" && (
            <input
              className="auth-input"
              placeholder="昵称（可选）"
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoComplete="nickname"
            />
          )}
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
          <input
            className="auth-input"
            type="password"
            placeholder={mode === "register" ? "密码（至少 8 位）" : "密码"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            minLength={8}
            required
          />
          {error && <p className="auth-error">{error}</p>}
          <button type="submit" className="auth-submit" disabled={submitting}>
            {submitting ? "处理中…" : mode === "login" ? "登录" : "注册并登录"}
          </button>
        </form>

        <p className="auth-hint">登录后，当前匿名的对话和记忆会自动并入你的账号。</p>
      </div>
    </div>
  );
}
