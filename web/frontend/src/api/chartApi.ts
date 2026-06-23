import { apiPost } from "./client";
import type { BirthInput, ChartResponse } from "../types/api";

export function castAndDiagnose(input: BirthInput): Promise<ChartResponse> {
  return apiPost<ChartResponse>("/chart", input);
}
