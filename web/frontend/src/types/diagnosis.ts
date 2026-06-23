/** Diagnosis-related types matching backend Diagnosis.to_dict() output. */

export interface Citation {
  rule_id: string;
  chapter: string;
  source_text: string;
  modern_summary: string;
  reason: string;
  conclusion: string;
}

export interface TransparentStem {
  stem: string;
  role: string;
  transparent_at: string;
}

export interface YongShen {
  stem: string;
  ten_god: string;
  source_rule_id: string;
  is_bi_jie: boolean;
  unresolved: boolean;
  alternative_source: string | null;
  transparent_stems: TransparentStem[];
  citations: Citation[];
}

export interface GeJu {
  name: string;
  alias: string | null;
  category: string;
  source_rule_id: string;
  unresolved: boolean;
  citations: Citation[];
}

export interface XiangShenItem {
  position: string;
  location: string;
  stem: string;
  ten_god: string;
}

export interface XiangShen {
  xiang_shen: XiangShenItem[];
  ji_shen: XiangShenItem[];
  notes: string[];
  citations: Citation[];
}

export interface ChengBai {
  verdict: string;
  source_rule_id: string;
  rescue_gods: XiangShenItem[];
  unresolved: boolean;
  citations: Citation[];
}

export interface InteractionItem {
  [key: string]: unknown;
}

export interface Interactions {
  gan_he: InteractionItem[];
  san_he: InteractionItem[];
  ban_he: InteractionItem[];
  san_hui: InteractionItem[];
  ban_hui: InteractionItem[];
  chong: InteractionItem[];
  xing: InteractionItem[];
  hai: InteractionItem[];
  citations: Citation[];
}

export interface Diagnosis {
  chart_summary: string;
  day_master: string;
  yong_shen: YongShen;
  ge_ju: GeJu;
  xiang_shen: XiangShen;
  cheng_bai: ChengBai;
  interactions: Interactions;
  all_citations: Citation[];
}
