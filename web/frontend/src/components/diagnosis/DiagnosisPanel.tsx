import type { Diagnosis } from "../../types/diagnosis";

const VERDICT_TAG: Record<string, string> = {
  成格: "tag-good",
  成: "tag-good",
  救应: "tag-neutral",
  败格: "tag-bad",
  败: "tag-bad",
};

export function DiagnosisPanel({ diagnosis }: { diagnosis: Diagnosis }) {
  const { yong_shen, ge_ju, xiang_shen, cheng_bai } = diagnosis;

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title">
          DIAGNOSIS <span className="cn">核心诊断</span>
        </div>
      </div>
      <div style={{ padding: 0 }}>
        {/* Day Master + Strength */}
        <div className="diag-cell">
          <div className="diag-label">DAY MASTER 日主</div>
          <div className="diag-value">
            {diagnosis.day_master}
            <span className={`tag ${diagnosis.chart_summary.includes("身弱") ? "tag-bad" : "tag-good"}`}>
              {diagnosis.chart_summary.includes("身弱") ? "身弱" : "身强"}
            </span>
          </div>
        </div>

        {/* Yong Shen */}
        <div className="diag-cell">
          <div className="diag-label">YONG SHEN 用神</div>
          <div className="diag-gods">
            <span className="god-chip yong">
              {yong_shen.stem} · {yong_shen.ten_god}
            </span>
          </div>
        </div>

        {/* Xiang Shen */}
        {xiang_shen.xiang_shen.length > 0 && (
          <div className="diag-cell">
            <div className="diag-label">XIANG SHEN 相神</div>
            <div className="diag-gods">
              {xiang_shen.xiang_shen.map((x, i) => (
                <span key={i} className="god-chip xiang">
                  {x.stem} · {x.ten_god}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Ji Shen */}
        {xiang_shen.ji_shen.length > 0 && (
          <div className="diag-cell">
            <div className="diag-label">JI SHEN 忌神</div>
            <div className="diag-gods">
              {xiang_shen.ji_shen.map((x, i) => (
                <span key={i} className="god-chip ji">
                  {x.stem} · {x.ten_god}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Ge Ju */}
        <div className="diag-cell">
          <div className="diag-label">GE JU 格局</div>
          <div className="diag-value">
            {ge_ju.name}
            {!ge_ju.unresolved && (
              <span className={`tag ${VERDICT_TAG[cheng_bai.verdict] || "tag-good"}`}>
                {cheng_bai.verdict}
              </span>
            )}
          </div>
        </div>

        {/* Cheng Bai */}
        <div className="diag-cell">
          <div className="diag-label">CHENG BAI 成败</div>
          <div className="diag-value">
            {cheng_bai.verdict}
            {cheng_bai.rescue_gods.length > 0 && (
              <span className="tag tag-good">
                {cheng_bai.rescue_gods.map((g) => g.stem).join("")}护
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
