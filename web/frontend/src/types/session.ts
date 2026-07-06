export type MessageRole = "user" | "assistant" | "system";

export type MessageFeedback = "like" | "dislike";

export type HiddenStem = {
  char: string;
  ten_god: string | null;
  role: string | null;
};

export type ChartPillar = {
  label: string;
  stem: string;
  stem_ten_god: string | null;
  branch: string;
  branch_ten_god: string | null;
  hidden: HiddenStem[];
  nayin: string | null;
};

/** One column of the 专业细盘 grid (流年/大运/年/月/日/时). */
export type ProColumn = {
  label: string;
  stem: string;
  stem_ten_god: string | null;
  branch: string;
  hidden: HiddenStem[];
  nayin: string | null;
  void_branches: string[];
  // Stage 2/3 enrichments (optional until wired):
  star_luck?: string | null; // 星运 (日主十二长生 on this branch)
  self_sit?: string | null; // 自坐 (this stem's 十二长生 on its own branch)
  shensha?: string[]; // 精选神煞
};

export type ChartLuckPillar = {
  stem_branch: string;
  start_year: number;
  end_year: number;
  start_age: number;
  end_age: number;
  stem_ten_god?: string;
  branch_ten_god?: string;
  // Full pro-grid columns for click-to-switch (this 大运 + each of its 流年).
  column?: ProColumn;
  years?: { year: number; column: ProColumn }[];
};

export type InteractionGroup = "合" | "冲" | "刑" | "害";

export type ChartInteraction = {
  group: InteractionGroup;
  kind: string;
  chars: string[];
  positions: string[];
  note: string;
};

export type ElementWeight = {
  el: string;
  count: number;
  pct: number;
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
  columns?: ProColumn[];
  elements?: ElementWeight[];
  interactions?: ChartInteraction[];
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
  /** 命盘主体:self/spouse/child/parent/other。后端返回,前端展示用。 */
  subject?: string | null;
};
