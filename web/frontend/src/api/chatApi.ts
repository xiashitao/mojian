import { apiGet } from "./client";
import type { ChatAnalysis, ChatRequest, ChatResponse } from "../types/api";

const BASE_URL = "/api";

export async function sendChatMessage(
  req: ChatRequest,
  onToken: (text: string) => void,
): Promise<ChatResponse> {
  const res = await fetch(`${BASE_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });

  if (!res.ok || !res.body) {
    throw new Error(`Chat request failed: ${res.statusText}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finalResponse: ChatResponse | null = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      try {
        const msg = JSON.parse(trimmed) as {
          type: string;
          text?: string;
          conversation_id?: string;
          analysis_id?: string;
          state?: ChatResponse["state"];
          detail?: string;
        };
        if (msg.type === "token" && msg.text) {
          onToken(msg.text);
        } else if (msg.type === "done") {
          finalResponse = {
            conversation_id: msg.conversation_id ?? "",
            analysis_id: msg.analysis_id ?? "",
            reply: "",
            state: msg.state ?? { topic: null, needs_more_info: false, missing_fields: [], suggested_followups: [] },
          };
        } else if (msg.type === "error") {
          throw new Error(msg.detail ?? "Unknown error");
        }
      } catch (e) {
        if (e instanceof SyntaxError) continue;
        throw e;
      }
    }
  }

  if (!finalResponse) {
    throw new Error("Stream ended without completion");
  }
  return finalResponse;
}

export function getChatAnalysis(analysisId: string): Promise<ChatAnalysis> {
  return apiGet<ChatAnalysis>(`/admin/analyses/${analysisId}`);
}

