const ANON_ID_KEY = "kairos-anon-id";

/** Stable anonymous id for memory, until the account system lands. */
export function getAnonId(): string {
  let id = localStorage.getItem(ANON_ID_KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(ANON_ID_KEY, id);
  }
  return id;
}
