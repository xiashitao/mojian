import { getAnonId } from "../utils/anonId";

const BASE_URL = "/api/auth";

export interface AuthUser {
  id: string;
  email: string;
  name: string;
  role: string;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json();
}

export function register(email: string, password: string, name: string): Promise<AuthUser> {
  return post<AuthUser>("/register", { email, password, name, anon_id: getAnonId() });
}

export function login(email: string, password: string): Promise<AuthUser> {
  return post<AuthUser>("/login", { email, password, anon_id: getAnonId() });
}

/** Send a login verification code to the email (OTP flow). */
export function sendEmailCode(
  email: string,
): Promise<{ ok: boolean; resend_after: number }> {
  return post("/email/send-code", { email });
}

/** Verify the code; on success the session cookie is set and the user returned. */
export function verifyEmailCode(email: string, code: string): Promise<AuthUser> {
  return post<AuthUser>("/email/verify", { email, code, anon_id: getAnonId() });
}

export function logout(): Promise<{ ok: boolean }> {
  return post<{ ok: boolean }>("/logout", {});
}

/** Current user from the session cookie, or null when signed out. */
export async function fetchMe(): Promise<AuthUser | null> {
  const res = await fetch(`${BASE_URL}/me`, { credentials: "include" });
  if (!res.ok) return null;
  return res.json();
}
