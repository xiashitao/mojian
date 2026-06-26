import { useState } from "react";
import { useAuth } from "../../auth";
import { AuthModal } from "./AuthModal";

/** Header account control: shows the signed-in user, or opens an auth modal. */
export function AccountMenu() {
  const { user, loading, logout } = useAuth();
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
      {open && <AuthModal onClose={() => setOpen(false)} />}
    </>
  );
}
