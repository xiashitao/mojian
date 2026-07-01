/** crypto.randomUUID() is unavailable over plain HTTP; fall back to getRandomValues. */
export function uuid(): string {
  if (typeof crypto.randomUUID === "function") return crypto.randomUUID();
  const a = crypto.getRandomValues(new Uint8Array(16));
  a[6] = (a[6] & 0x0f) | 0x40;
  a[8] = (a[8] & 0x3f) | 0x80;
  const h = [...a].map((b) => b.toString(16).padStart(2, "0")).join("");
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`;
}

const ANON_ID_KEY = "kairos-anon-id";

/** Stable anonymous id for memory, until the account system lands. */
export function getAnonId(): string {
  let id = localStorage.getItem(ANON_ID_KEY);
  if (!id) {
    id = uuid();
    localStorage.setItem(ANON_ID_KEY, id);
  }
  return id;
}
