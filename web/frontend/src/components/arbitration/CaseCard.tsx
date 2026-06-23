import type { ArbitrationCaseItem, ArbitrationResponseItem } from "../../types/api";

interface CaseCardProps {
  caseItem: ArbitrationCaseItem;
  response?: ArbitrationResponseItem;
  error?: string;
}

const CATEGORY_CLASS: Record<string, string> = {
  rescue: "case-rescue",
  conflict: "case-conflict",
};

function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.75) return "var(--accent-green)";
  if (confidence >= 0.5) return "var(--accent-amber)";
  return "var(--accent-red)";
}

export function CaseCard({ caseItem, response, error }: CaseCardProps) {
  const catClass = CATEGORY_CLASS[caseItem.category] || "case-rescue";

  return (
    <div className="case-card">
      <div className="case-header">
        <span className={`case-category ${catClass}`}>
          {caseItem.category.toUpperCase()}
        </span>
        <span className="case-title">{caseItem.title}</span>
        <span className={`case-status ${error ? "fail" : response ? "ok" : "pending"}`}>
          {error ? "FAIL" : response ? "OK" : "..."}
        </span>
      </div>
      <div className="case-body">
        <p style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 8 }}>
          {caseItem.description}
        </p>

        {/* Evidence */}
        {caseItem.options.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 8 }}>
            {caseItem.options.map((opt) => (
              <span
                key={opt}
                style={{
                  fontSize: 10,
                  fontFamily: "var(--font-mono)",
                  color: "var(--text-muted)",
                  background: "var(--bg-elevated)",
                  padding: "2px 6px",
                  borderRadius: 3,
                }}
              >
                {opt}
              </span>
            ))}
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="case-response">
            <p style={{ fontSize: 12, color: "var(--accent-red)" }}>
              仲裁失败：{error}
            </p>
          </div>
        )}

        {/* Response */}
        {response && (
          <div className="case-response">
            <div className="response-decision">
              <span className="response-decision-text">{response.decision}</span>
              <div className="confidence-bar">
                <div
                  className="confidence-fill"
                  style={{
                    width: `${response.confidence * 100}%`,
                    background: getConfidenceColor(response.confidence),
                  }}
                />
              </div>
              <span
                className="confidence-value"
                style={{ color: getConfidenceColor(response.confidence) }}
              >
                {(response.confidence * 100).toFixed(0)}%
              </span>
              {response.is_unresolved && (
                <span style={{
                  fontSize: 9,
                  fontFamily: "var(--font-mono)",
                  color: "var(--accent-amber)",
                  background: "rgba(245,158,11,0.15)",
                  padding: "1px 6px",
                  borderRadius: 3,
                }}>
                  UNRESOLVED
                </span>
              )}
            </div>
            <div className="response-reasoning">{response.reasoning}</div>
            {response.cited_rules.length > 0 && (
              <div className="response-rules">
                {response.cited_rules.map((rule, i) => (
                  <span key={i} className="response-rule-chip">{rule}</span>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
