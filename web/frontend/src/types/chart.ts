/** Chart-related types matching backend Chart.to_dict() output. */

export type ElementName = "木" | "火" | "土" | "金" | "水";

export type TenGod =
  | "日主"
  | "比肩"
  | "劫财"
  | "食神"
  | "伤官"
  | "偏财"
  | "正财"
  | "正官"
  | "七杀"
  | "正印"
  | "偏印";

export interface HiddenStem {
  char: string;
  role: string;
  ten_god: string;
}

export interface StemInfo {
  char: string;
  ten_god: string;
  relative?: string;
}

export interface BranchInfo {
  char: string;
  hidden_stems: HiddenStem[];
  ten_god: string;
  relative?: string;
}

export interface Pillar {
  name_cn: string;
  stem_branch: string;
  stem: StemInfo;
  branch: BranchInfo;
  nayin?: string;
  void_branches?: string[];
  branch_is_void?: boolean;
}

export interface FourPillars {
  year: Pillar;
  month: Pillar;
  day: Pillar;
  hour: Pillar;
}

export interface StrengthBreakdown {
  source: string;
  contribution: number;
  note: string;
}

export interface Strength {
  total_score: number;
  verdict: string;
  borderline: boolean;
  breakdown: StrengthBreakdown[];
}

export interface LuckPillar {
  index: number;
  stem_branch: string;
  start_age: number;
  end_age: number;
  start_year: number;
  end_year: number;
  stem_ten_god?: string;
  stem_relative?: string;
  branch_ten_god?: string;
  branch_relative?: string;
}

export interface Luck {
  direction: string;
  start_age: { years: number; months: number; days: number };
  start_solar: string;
  pillars: LuckPillar[];
}

export interface ChartInput {
  birth_clock_time: string;
  longitude: number;
  tz_offset_hours: number;
  gender: string;
}

export interface ElementDistribution {
  [key: string]: { count: number; percentage: number };
}

export interface Chart {
  input: ChartInput;
  true_solar_time: string;
  day_master: string;
  day_master_element: string;
  four_pillars: FourPillars;
  strength: Strength;
  luck: Luck;
  void_info?: Record<string, string[]>;
  element_distribution?: ElementDistribution;
  element_total?: number;
}
