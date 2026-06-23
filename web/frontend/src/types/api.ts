import type { Chart } from "./chart";
import type { Diagnosis } from "./diagnosis";

export interface BirthInput {
  date: string;
  time: string;
  longitude: number;
  gender: "male" | "female";
  tz_offset_hours: number;
  apply_solar_time_correction: boolean;
}

export interface ChartResponse {
  chart: Chart;
  diagnosis: Diagnosis;
}

export interface SavedChart {
  id: string;
  label: string;
  date: string;
  time: string;
  longitude: number;
  gender: string;
  tz_offset: number;
  solar_correction: number;
  created_at: string;
  updated_at: string;
}

export interface SaveChartRequest {
  label: string;
  date: string;
  time: string;
  longitude: number;
  gender: string;
  tz_offset: number;
  solar_correction: number;
}

export interface ArbitrationCaseItem {
  case_id: string;
  category: string;
  title: string;
  description: string;
  evidence: unknown;
  options: string[];
  relevant_rules: string[];
}

export interface ArbitrationResponseItem {
  decision: string;
  reasoning: string;
  confidence: number;
  cited_rules: string[];
  raw_response: string;
  is_unresolved: boolean;
}

export interface ArbitrationSummary {
  total: number;
  resolved: number;
  unresolved: number;
  errors: number;
}

export interface ArbitrationResult {
  cases: ArbitrationCaseItem[];
  responses: Record<string, ArbitrationResponseItem>;
  errors: Record<string, string>;
  summary: ArbitrationSummary;
}

export interface ArbitrateResponse {
  chart: Chart;
  diagnosis: Diagnosis;
  arbitration: ArbitrationResult;
}

export interface ChatState {
  topic: "career" | "relationship" | "wealth" | "personality" | null;
  needs_more_info: boolean;
  missing_fields: string[];
  suggested_followups: string[];
}

export interface ChatResponse {
  conversation_id: string;
  analysis_id: string;
  reply: string;
  state: ChatState;
}

export interface ChatRequest {
  conversation_id?: string;
  message: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  analysis_id: string | null;
  created_at?: string;
}

export type Topic = "career" | "relationship" | "wealth" | "personality" | null;

export interface ConversationSummary {
  id: string;
  title: string;
  topic: Topic;
  gender: string | null;
  message_count: number;
  excerpt: string;
  created_at: string;
  updated_at: string;
  last_message_at: string | null;
}

export interface ConversationMessage {
  id: string;
  conversation_id: string;
  role: string;
  content: string;
  analysis_id: string | null;
  created_at: string;
}

export interface ConversationDetail {
  conversation_id: string;
  messages: ConversationMessage[];
  state: Record<string, unknown>;
}

export interface ChatAnalysis {
  analysis: {
    analysis_id: string;
    status: string;
    intent: string | null;
    topic: string | null;
    latency_ms: number | null;
    error: string | null;
  };
  conversation: unknown;
  messages: ChatMessage[];
  agent_run: unknown;
  run_traces: Array<{
    id: string;
    run_id: string;
    step_index: number;
    step_type: string;
    input_json: unknown;
    output_json: unknown;
    summary: string | null;
    created_at: string;
  }>;
  chart: unknown;
  diagnosis: unknown;
  arbitration: unknown;
  llm: unknown;
}
