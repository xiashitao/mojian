import { useEffect, useRef, useState } from "react";
import { useAuth } from "../../auth";
import { AuthModal } from "./AuthModal";

/** Header account control: signed-out shows a 登录 button; signed-in shows the
 *  user name that reveals a 退出登录 menu on hover or click. */
export function AccountMenu() {
  const { user, loading, logout } = useAuth();
  const [authOpen, setAuthOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Close the dropdown on outside click / Escape.
  useEffect(() => {
    if (!menuOpen) return;
    const onDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setMenuOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMenuOpen(false);
    };
    window.addEventListener("mousedown", onDown);
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("mousedown", onDown);
      window.removeEventListener("keydown", onKey);
    };
  }, [menuOpen]);

  if (loading) return null;

  if (user) {
    return (
      <div
        className="account account--menu"
        ref={ref}
        onMouseEnter={() => setMenuOpen(true)}
        onMouseLeave={() => setMenuOpen(false)}
      >
        <button
          type="button"
          className="account__trigger"
          onClick={() => setMenuOpen((o) => !o)}
          aria-haspopup="menu"
          aria-expanded={menuOpen}
        >
          <span className="account__name">{user.name || user.email}</span>
          {user.role !== "user" && <span className="account__role">{user.role}</span>}
        </button>
        {menuOpen && (
          <div className="account__dropdown" role="menu">
            <button
              type="button"
              className="account__dropdown-item"
              role="menuitem"
              onClick={() => void logout()}
            >
              退出登录
            </button>
          </div>
        )}
      </div>
    );
  }

  return (
    <>
      <button
        type="button"
        className="account__login"
        onClick={() => setAuthOpen(true)}
      >
        登录
      </button>
      {authOpen && <AuthModal onClose={() => setAuthOpen(false)} />}
    </>
  );
}
