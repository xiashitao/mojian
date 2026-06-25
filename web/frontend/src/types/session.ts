export type MessageRole = "user" | "assistant" | "system";

export type MessageFeedback = "like" | "dislike";

export type ChartPillar = {
  label: string;
  stem: string;
  stem_ten_god: string | null;
  branch: string;
  branch_ten_god: string | null;
  hidden: string[];
  nayin: string | null;
};

export type ChartLuckPillar = {
  stem_branch: string;
  start_year: number;
  end_year: number;
  start_age: number;
  stem_ten_god?: string;
  branch_ten_god?: string;
};

export type ChartCurrent = {
  year: number;
  nominal_age: number;
  liunian: string;
  liunian_stem_ten_god?: string;
  liunian_branch_ten_god?: string;
  luck_index: number;
  luck_stem_branch: string;
};

export type ChartData = {
  day_master: string;
  day_master_element: string;
  pillars: ChartPillar[];
  luck: { direction: string | null; pillars: ChartLuckPillar[] };
  current: ChartCurrent | null;
  birth: {
    date: string | null;
    time: string | null;
    place: string | null;
    gender: string | null;
  };
};

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
  chart?: ChartData;
};

export type BirthInfo = {
  birth_date?: string | null;
  birth_time?: string | null;
  birth_place?: string | null;
  gender?: string | null;
  longitude?: number | null;
};
