import type { ArbitrationResult } from "../../types/api";
import { CaseCard } from "./CaseCard";

interface ArbitrationPanelProps {
  result: ArbitrationResult | null;
  loading: boolean;
}

export function ArbitrationPanel({ result, loading }: ArbitrationPanelProps) {
  if (loading) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">⏳</div>
        <p style={{ fontSize: 14 }}>正在调用 DeepSeek 仲裁，请稍候…</p>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">⚖</div>
        <p style={{ fontSize: 14 }}>排盘后点击「触发 LLM 仲裁」按钮开始分析</p>
      </div>
    );
  }

  const { summary } = result;

  return (
    <div>
      {/* Summary bar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 16,
          marginBottom: 16,
          padding: "10px 16px",
          background: "var(--bg-panel)",
          border: "1px solid var(--border-default)",
          borderRadius: 8,
        }}
      >
        <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--text-muted)" }}>
          已解决: <span style={{ color: "var(--accent-green)", fontWeight: 600 }}>{summary.resolved}</span>
        </span>
        <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--text-muted)" }}>
          未解决: <span style={{ color: "var(--accent-amber)", fontWeight: 600 }}>{summary.unresolved}</span>
        </span>
        <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--text-muted)" }}>
          错误: <span style={{ color: "var(--accent-red)", fontWeight: 600 }}>{summary.errors}</span>
        </span>
        <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--text-muted)", marginLeft: "auto" }}>
          总计: {summary.total}
        </span>
      </div>

      {result.cases.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">✓</div>
          <p style={{ fontSize: 14 }}>无争议点，诊断一致。</p>
        </div>
      ) : (
        result.cases.map((c) => (
          <CaseCard
            key={c.case_id}
            caseItem={c}
            response={result.responses[c.case_id]}
            error={result.errors[c.case_id]}
          />
        ))
      )}
    </div>
  );
}
