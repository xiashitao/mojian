import { apiGet, apiPost } from "./client";
import type { ChatAnalysis, ChatRequest, ChatResponse } from "../types/api";

export function sendChatMessage(req: ChatRequest): Promise<ChatResponse> {
  return apiPost<ChatResponse>("/chat", req);
}

export function getChatAnalysis(analysisId: string): Promise<ChatAnalysis> {
  return apiGet<ChatAnalysis>(`/admin/analyses/${analysisId}`);
}

