import { apiGet } from "./client";
import type { ConversationRun } from "./chatApi";

/** 一条用户反馈(运营定位入口)。 */
export interface FeedbackItem {
  feedback: "like" | "dislike";
  comment: string | null;
  feedback_at: string | null;
  analysis_id: string;
  conversation_id: string;
  reply_excerpt: string | null;
  user_message: string | null;
  intent: string | null;
  topic: string | null;
}

/** 最近一轮 run 的概要(运营浏览入口)。 */
export interface RecentRun {
  run_id: string;
  analysis_id: string;
  conversation_id: string;
  status: string;
  intent: string | null;
  topic: string | null;
  latency_ms: number | null;
  started_at: string;
  error: string | null;
  llm_calls: number | null;
  total_tokens: number | null;
  cost: number | null;
}

export interface AdminMessage {
  id: string;
  conversation_id: string;
  role: string;
  content: string;
  analysis_id: string | null;
  created_at: string;
  metadata_json: string | null;
}

export interface AdminConversation {
  conversation: { id: string; title: string | null; created_at: string };
  messages: AdminMessage[];
  runs: ConversationRun[];
}

export function getAdminFeedback(days = 30): Promise<{ feedback: FeedbackItem[] }> {
  return apiGet(`/admin/feedback?days=${days}`);
}

export function getAdminRuns(limit = 30): Promise<{ runs: RecentRun[] }> {
  return apiGet(`/admin/runs?limit=${limit}`);
}

export function getAdminConversation(id: string): Promise<AdminConversation> {
  return apiGet(`/admin/conversations/${encodeURIComponent(id)}`);
}
