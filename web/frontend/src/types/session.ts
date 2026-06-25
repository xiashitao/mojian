export type MessageRole = "user" | "assistant" | "system";

export type MessageFeedback = "like" | "dislike";

export type UiMessage = {
  id: string;
  role: MessageRole;
  content: string;
  analysis_id: string | null;
  created_at?: string;
  followups?: string[];
  pending?: boolean;
  error?: boolean;
  feedback?: MessageFeedback | null;
};

export type BirthInfo = {
  birth_date?: string | null;
  birth_time?: string | null;
  birth_place?: string | null;
  gender?: string | null;
  longitude?: number | null;
};
