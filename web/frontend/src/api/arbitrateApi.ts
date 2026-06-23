import { apiPost } from "./client";
import type { BirthInput, ArbitrateResponse } from "../types/api";

export function runArbitration(
  input: BirthInput & { threshold?: number },
): Promise<ArbitrateResponse> {
  return apiPost<ArbitrateResponse>("/arbitrate", input);
}
