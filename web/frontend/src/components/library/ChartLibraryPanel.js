import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useState } from "react";
import { useChartLibraryStore } from "../../stores/useChartLibraryStore";
export function ChartLibraryPanel({ onLoad }) {
    const { charts, loading, error, fetchCharts, removeChart } = useChartLibraryStore();
    const [search, setSearch] = useState("");
    useEffect(() => {
        fetchCharts();
    }, [fetchCharts]);
    const handleSearch = (q) => {
        setSearch(q);
        fetchCharts(q);
    };
    return (_jsxs("div", { className: "card", children: [_jsxs("div", { className: "card-header", children: [_jsxs("div", { className: "card-title", children: ["SAVED CHARTS ", _jsx("span", { className: "cn", children: "\u547D\u4F8B\u5E93" })] }), _jsx("input", { type: "text", placeholder: "\u641C\u7D22\u2026", value: search, onChange: (e) => handleSearch(e.target.value), style: {
                            background: "var(--bg-card)",
                            border: "1px solid var(--border-default)",
                            borderRadius: 4,
                            padding: "4px 10px",
                            color: "var(--text-primary)",
                            fontSize: 12,
                            width: 200,
                            fontFamily: "var(--font-mono)",
                            outline: "none",
                        } })] }), loading && (_jsx("div", { className: "empty-state", children: _jsx("p", { style: { fontSize: 15 }, children: "\u52A0\u8F7D\u4E2D\u2026" }) })), error && (_jsx("div", { className: "empty-state", children: _jsx("p", { style: { fontSize: 15, color: "var(--accent-red)" }, children: error }) })), !loading && !error && (_jsx("div", { children: charts.length === 0 ? (_jsxs("div", { className: "empty-state", children: [_jsx("div", { className: "empty-state-icon", children: "\uD83D\uDCCB" }), _jsx("p", { style: { fontSize: 15 }, children: search ? "没有匹配的命例" : "暂无保存的命例" })] })) : (charts.map((chart) => {
                    const input = {
                        date: chart.date,
                        time: chart.time,
                        longitude: chart.longitude,
                        gender: chart.gender,
                        tz_offset_hours: chart.tz_offset,
                        apply_solar_time_correction: chart.solar_correction === 1,
                    };
                    return (_jsxs("div", { className: "library-item", onClick: () => onLoad(input), children: [_jsxs("div", { children: [_jsx("div", { className: "library-label", children: chart.label }), _jsxs("div", { style: {
                                            fontFamily: "var(--font-mono)",
                                            fontSize: 12,
                                            color: "var(--text-muted)",
                                            marginTop: 2,
                                        }, children: ["id: ", chart.id, " \u00B7 ", chart.date, " ", chart.time, " \u00B7", " ", chart.longitude, "\u00B0E \u00B7 ", chart.gender === "male" ? "男" : "女"] })] }), _jsx("div", { className: "library-ganzhi", children: "\u2014" }), _jsxs("div", { className: "library-date", children: [chart.created_at.split(" ")[0], " \u521B\u5EFA"] }), _jsx("button", { className: "library-action", onClick: (e) => {
                                    e.stopPropagation();
                                    removeChart(chart.id);
                                }, children: "\u5220\u9664" })] }, chart.id));
                })) }))] }));
}
