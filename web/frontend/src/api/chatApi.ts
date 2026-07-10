import { apiGet } from "./client";
import { getAnonId } from "../utils/anonId";
import type { ChartData } from "../types/session";
import type { ChatAnalysis, ChatRequest, ChatResponse } from "../types/api";

const BASE_URL = "/api";

/** Thrown when the chat endpoint rejects an unauthenticated request (401). */
export class AuthRequiredError extends Error {
  constructor() {
    super("需要登录后才能使用对话");
    this.name = "AuthRequiredError";
  }
}

// 切换为 true 可完全不启动后端，在浏览器内验证流式 UI
const MOCK_MODE = import.meta.env.VITE_MOCK_CHAT === "true";

const _MOCK_REPLY =
  "根据你的命盘结构来看，日主偏强，用神倾向食伤泄秀。" +
  "事业上比较适合在专业领域深耕，靠能力和作品建立信用，" +
  "而不是靠人脉和资源驱动的方向。\n\n" +
  "当前运势处于过渡期，适合稳固现有基础，" +
  "不宜大规模扩张或冒险性投入。明年下半年开始，" +
  "会进入一个相对顺畅的阶段，可以考虑做一些中期布局。\n\n" +
  "你可以继续问：适合哪个行业方向？ / 明年有什么需要注意的？";

async function _mockStream(
  onToken: (text: string) => void,
): Promise<ChatResponse> {
  const chunkSize = 3;
  for (let i = 0; i < _MOCK_REPLY.length; i += chunkSize) {
    const chunk = _MOCK_REPLY.slice(i, i + chunkSize);
    onToken(chunk);
    await new Promise((r) => setTimeout(r, 50));
  }
  return {
    conversation_id: "mock-conv-001",
    analysis_id: "mock-analysis-001",
    reply: _MOCK_REPLY,
    state: {
      topic: "career",
      needs_more_info: false,
      missing_fields: [],
      suggested_followups: ["适合哪个行业方向？", "明年有什么需要注意的？"],
    },
  };
}

export async function sendChatMessage(
  req: ChatRequest,
  onToken: (text: string) => void,
  signal?: AbortSignal,
  onChart?: (chart: ChartData) => void,
  onSubjectConfirmation?: (birthInfo: Record<string, unknown>) => void,
): Promise<ChatResponse> {
  if (MOCK_MODE) return _mockStream(onToken);

  const endpoint = `${BASE_URL}/chat`;
  const res = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ ...req, anon_id: getAnonId() }),
    signal,
  });

  if (res.status === 401) {
    throw new AuthRequiredError();
  }
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
          chart?: ChartData;
          birth_info?: Record<string, unknown>;
          conversation_id?: string;
          analysis_id?: string;
          state?: ChatResponse["state"];
          detail?: string;
        };
        if (msg.type === "token" && msg.text) {
          onToken(msg.text);
        } else if (msg.type === "chart" && msg.chart) {
          onChart?.(msg.chart);
        } else if (msg.type === "needs_subject_confirmation" && msg.birth_info) {
          // 后端检测到八字但主体不明。通知前端弹"这是哪位的?"对话框。
          // 用户选完后,前端带 subject 重发同一条消息(req.message 仍是原消息)。
          onSubjectConfirmation?.(msg.birth_info);
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

/** 一段会话里每轮 run 的概要 + LLM 聚合(跨轮追踪时间线)。Admin only. */
export interface ConversationRun {
  analysis_id: string;
  status: string;
  intent: string | null;
  topic: string | null;
  latency_ms: number | null;
  started_at: string;
  error: string | null;
  user_message: string;
  llm_calls: number;
  total_tokens: number;
}

export function getConversationRuns(
  conversationId: string,
): Promise<{ runs: ConversationRun[] }> {
  return apiGet<{ runs: ConversationRun[] }>(
    `/admin/conversations/${conversationId}/runs`,
  );
}
