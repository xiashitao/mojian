import { apiGet, apiPost } from "./client";
import { getAnonId } from "../utils/anonId";
import type {
  ConversationDetail,
  ConversationSummary,
} from "../types/api";

export function listConversations(): Promise<ConversationSummary[]> {
  const anon = encodeURIComponent(getAnonId());
  return apiGet<ConversationSummary[]>(`/conversations?anon_id=${anon}`);
}

export function getConversation(id: string): Promise<ConversationDetail> {
  const anon = encodeURIComponent(getAnonId());
  return apiGet<ConversationDetail>(`/conversations/${id}?anon_id=${anon}`);
}

/** 提交/撤销一轮回复的反馈(feedback=null 为撤销)。以 analysis_id 为键。 */
export function postFeedback(
  analysisId: string,
  feedback: "like" | "dislike" | null,
  comment?: string,
): Promise<{ analysis_id: string; feedback: string | null }> {
  return apiPost(`/feedback`, {
    analysis_id: analysisId,
    feedback,
    comment,
    anon_id: getAnonId(),
  });
}
