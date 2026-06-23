import { apiGet, apiPost, apiDelete } from "./client";
import type { SavedChart, SaveChartRequest } from "../types/api";

export function listCharts(q?: string): Promise<SavedChart[]> {
  const query = q ? `?q=${encodeURIComponent(q)}` : "";
  return apiGet<SavedChart[]>(`/charts${query}`);
}

export function saveChart(req: SaveChartRequest): Promise<SavedChart> {
  return apiPost<SavedChart>("/charts", req);
}

export function deleteChart(id: string): Promise<{ deleted: string }> {
  return apiDelete<{ deleted: string }>(`/charts/${id}`);
}
