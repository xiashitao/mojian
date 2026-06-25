import { apiGet } from "./client";
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
