import { useEffect, useState } from "react";
import type { BirthInput } from "../../types/api";
import { useChartLibraryStore } from "../../stores/useChartLibraryStore";

interface ChartLibraryPanelProps {
  onLoad: (input: BirthInput) => void;
}

export function ChartLibraryPanel({ onLoad }: ChartLibraryPanelProps) {
  const { charts, loading, error, fetchCharts, removeChart } =
    useChartLibraryStore();
  const [search, setSearch] = useState("");

  useEffect(() => {
    fetchCharts();
  }, [fetchCharts]);

  const handleSearch = (q: string) => {
    setSearch(q);
    fetchCharts(q);
  };

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title">
          SAVED CHARTS <span className="cn">命例库</span>
        </div>
        <input
          type="text"
          placeholder="搜索…"
          value={search}
          onChange={(e) => handleSearch(e.target.value)}
          style={{
            background: "var(--bg-card)",
            border: "1px solid var(--border-default)",
            borderRadius: 4,
            padding: "4px 10px",
            color: "var(--text-primary)",
            fontSize: 12,
            width: 200,
            fontFamily: "var(--font-mono)",
            outline: "none",
          }}
        />
      </div>

      {loading && (
        <div className="empty-state">
          <p style={{ fontSize: 15 }}>加载中…</p>
        </div>
      )}

      {error && (
        <div className="empty-state">
          <p style={{ fontSize: 15, color: "var(--accent-red)" }}>{error}</p>
        </div>
      )}

      {!loading && !error && (
        <div>
          {charts.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">📋</div>
              <p style={{ fontSize: 15 }}>
                {search ? "没有匹配的命例" : "暂无保存的命例"}
              </p>
            </div>
          ) : (
            charts.map((chart) => {
              const input: BirthInput = {
                date: chart.date,
                time: chart.time,
                longitude: chart.longitude,
                gender: chart.gender as "male" | "female",
                tz_offset_hours: chart.tz_offset,
                apply_solar_time_correction: chart.solar_correction === 1,
              };
              return (
                <div
                  key={chart.id}
                  className="library-item"
                  onClick={() => onLoad(input)}
                >
                  <div>
                    <div className="library-label">{chart.label}</div>
                    <div
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: 12,
                        color: "var(--text-muted)",
                        marginTop: 2,
                      }}
                    >
                      id: {chart.id} · {chart.date} {chart.time} ·{" "}
                      {chart.longitude}°E · {chart.gender === "male" ? "男" : "女"}
                    </div>
                  </div>
                  <div className="library-ganzhi">—</div>
                  <div className="library-date">{chart.created_at.split(" ")[0]} 创建</div>
                  <button
                    className="library-action"
                    onClick={(e) => {
                      e.stopPropagation();
                      removeChart(chart.id);
                    }}
                  >
                    删除
                  </button>
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}
