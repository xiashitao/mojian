import { useState, type FormEvent } from "react";
import { useAuth } from "../../auth";

type Mode = "login" | "register";

/** Header account control: shows the signed-in user, or opens an auth modal. */
export function AccountMenu() {
  const { user, loading, login, register, logout } = useAuth();
  const [open, setOpen] = useState(false);

  if (loading) return null;

  if (user) {
    return (
      <div className="account">
        <span className="account__name">{user.name || user.email}</span>
        {user.role !== "user" && <span className="account__role">{user.role}</span>}
        <button type="button" className="account__link" onClick={() => void logout()}>
          退出
        </button>
      </div>
    );
  }

  return (
    <>
      <button type="button" className="account__login" onClick={() => setOpen(true)}>
        登录
      </button>
      {open && (
        <AuthModal onClose={() => setOpen(false)} login={login} register={register} />
      )}
    </>
  );
}

interface AuthModalProps {
  onClose: () => void;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
}

function AuthModal({ onClose, login, register }: AuthModalProps) {
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

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
      <div className="auth-modal" onClick={(e) => e.stopPropagation()}>
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
