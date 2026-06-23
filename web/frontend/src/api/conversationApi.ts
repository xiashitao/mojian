import { apiGet } from "./client";
import type {
  ConversationDetail,
  ConversationSummary,
} from "../types/api";

export function listConversations(): Promise<ConversationSummary[]> {
  return apiGet<ConversationSummary[]>("/conversations");
}

export function getConversation(id: string): Promise<ConversationDetail> {
  return apiGet<ConversationDetail>(`/conversations/${id}`);
}
