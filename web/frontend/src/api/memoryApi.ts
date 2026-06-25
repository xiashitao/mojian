import { apiPost } from "./client";
import { getAnonId } from "../utils/anonId";

/** Clear the user's remembered birth info (and any future memory). */
export function forgetMemory(): Promise<{ ok: boolean }> {
  return apiPost<{ ok: boolean }>("/memory/forget", { anon_id: getAnonId() });
}
