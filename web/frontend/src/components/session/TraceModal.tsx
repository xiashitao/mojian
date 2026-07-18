import { useEffect, useRef, useState } from "react";
import { getChatAnalysis } from "../../api/chatApi";
import type { ChatAnalysis } from "../../types/api";

interface Props {
  analysisId: string;
  onClose: () => void;
}

type TraceStep = ChatAnalysis["run_traces"][number];

/** 一步的 output_json 在 llm_call 时携带的调用元数据(见后端 agent/obs.py)。 */
interface LlmOutput {
  ok?: boolean;
  model?: string;
  provider?: string;
  stream?: boolean;
  latency_ms?: number;
  attempts?: number;
  total_tokens?: number;
  prompt_tokens?: number;
  completion_tokens?: number;
  cost?: number; // 元(CNY),CostMeter 按记录时定价写入;无定价模型时缺省
  cached?: boolean; // tool_call:结果是否来自工具缓存
  error?: string;
}

const STEP_LABEL: Record<string, string> = {
  extract_input: "意图抽取",
  merge_session_state: "合并会话状态",
  cast_chart: "排盘",
  diagnose: "诊断",
  prepare_arbitration: "准备仲裁",
  generate_reply: "生成回复",
  confirm_subject: "确认主体",
  update_memory: "更新记忆",
  update_memory_error: "记忆写入失败",
  update_profile: "更新画像",
  update_profile_error: "画像更新失败",
  persist_state: "落盘状态",
  persist_error: "持久化失败",
  hook_block: "hook 拦截",
  error: "运行出错",
  llm_call: "模型调用",
  tool_call: "工具调用",
};

function stepLabel(t: string): string {
  return STEP_LABEL[t] ?? t;
}

function pretty(value: unknown): string {
  if (value == null) return "";
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

/** 管理员追踪视图:一轮 run 的完整调用链——每步做了什么、每次模型调用多久多少 token。 */
export function TraceModal({ analysisId, onClose }: Props) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const [data, setData] = useState<ChatAnalysis | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    getChatAnalysis(analysisId)
      .then((d) => alive && setData(d))
      .catch((e) => alive && setError(e?.message ?? "加载失败"));
    return () => {
      alive = false;
    };
  }, [analysisId]);

  useEffect(() => {
    dialogRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const steps = data?.run_traces ?? [];
  const llmSteps = steps.filter((s) => s.step_type === "llm_call");
  const totalTokens = llmSteps.reduce(
    (n, s) => n + ((s.output_json as LlmOutput)?.total_tokens ?? 0),
    0,
  );
  const totalCost = llmSteps.reduce(
    (n, s) => n + ((s.output_json as LlmOutput)?.cost ?? 0),
    0,
  );

  return (
    <div className="detail-scrim" onClick={onClose}>
      <div
        className="detail-modal trace-modal"
        role="dialog"
        aria-modal="true"
        aria-label="调用追踪"
        tabIndex={-1}
        ref={dialogRef}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="detail-modal__head">
          <span className="detail-modal__title">调用追踪</span>
          <button
            type="button"
            className="detail-modal__close"
            onClick={onClose}
            aria-label="关闭"
          >
            ✕
          </button>
        </div>

        <div className="detail-modal__body">
          {error && <div className="trace-error">{error}</div>}
          {!data && !error && <div className="trace-placeholder">加载中…</div>}

          {data && (
            <>
              <div className="trace-head">
                <code className="trace-head__id">{analysisId}</code>
                <div className="trace-head__stats">
                  <span className={`trace-chip trace-chip--${data.analysis.status}`}>
                    {data.analysis.status}
                  </span>
                  {data.analysis.intent && (
                    <span className="trace-chip">{data.analysis.intent}</span>
                  )}
                  {data.analysis.topic && (
                    <span className="trace-chip">{data.analysis.topic}</span>
                  )}
                  {data.analysis.latency_ms != null && (
                    <span className="trace-chip">{data.analysis.latency_ms}ms</span>
                  )}
                  <span className="trace-chip">
                    {llmSteps.length} 次模型 · {totalTokens} tok
                    {totalCost > 0 ? ` · ¥${totalCost.toFixed(4)}` : ""}
                  </span>
                </div>
                {data.analysis.error && (
                  <div className="trace-error">{data.analysis.error}</div>
                )}
              </div>

              <ol className="trace-timeline">
                {steps.map((s) => (
                  <TraceRow key={s.id} step={s} />
                ))}
              </ol>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function TraceRow({ step }: { step: TraceStep }) {
  const isLlm = step.step_type === "llm_call";
  // 外部调用类步骤(llm_call/tool_call/mcp_call…)统一显示调用元信息行
  const isCall = step.step_type.endsWith("_call");
  const out = (step.output_json ?? {}) as LlmOutput;
  const failed = step.step_type === "error" || out.ok === false;

  return (
    <li className={`trace-step ${isCall ? "trace-step--llm" : ""} ${failed ? "trace-step--fail" : ""}`}>
      <div className="trace-step__head">
        <span className="trace-step__idx">{step.step_index}</span>
        <span className="trace-step__type">{stepLabel(step.step_type)}</span>
        {isCall && (
          <span className="trace-step__meta">
            {out.model}
            {out.stream ? " · 流式" : ""}
            {out.latency_ms != null ? ` · ${out.latency_ms}ms` : ""}
            {out.cached != null ? (out.cached ? " · 缓存命中" : " · 实算") : ""}
            {out.total_tokens != null ? ` · ${out.total_tokens}tok` : ""}
            {out.cost != null ? ` · ¥${out.cost.toFixed(4)}` : ""}
            {out.attempts && out.attempts > 1 ? ` · ${out.attempts}次` : ""}
          </span>
        )}
      </div>
      {step.summary && !isCall && (
        <div className="trace-step__summary">{step.summary}</div>
      )}
      <details className="trace-step__detail">
        <summary>详情</summary>
        {step.input_json != null && (
          <>
            <div className="trace-step__label">input</div>
            <pre className="trace-json">{pretty(step.input_json)}</pre>
          </>
        )}
        {step.output_json != null && (
          <>
            <div className="trace-step__label">output</div>
            <pre className="trace-json">{pretty(step.output_json)}</pre>
          </>
        )}
      </details>
    </li>
  );
}
