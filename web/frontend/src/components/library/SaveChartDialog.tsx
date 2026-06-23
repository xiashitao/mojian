import { useState } from "react";
import type { BirthInput } from "../../types/api";

interface SaveChartDialogProps {
  input: BirthInput;
  onSave: (label: string) => Promise<void>;
  onClose: () => void;
}

export function SaveChartDialog({ input, onSave, onClose }: SaveChartDialogProps) {
  const [label, setLabel] = useState("");
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      await onSave(
        label || `${input.date} ${input.gender === "male" ? "男" : "女"}`,
      );
      onClose();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.6)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 50,
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: "var(--bg-panel)",
          border: "1px solid var(--border-default)",
          borderRadius: 8,
          padding: 24,
          width: 400,
          maxWidth: "90vw",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16, color: "var(--text-primary)" }}>
          保存命例
        </h3>
        <div style={{ marginBottom: 16 }}>
          <input
            type="text"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder="命例名称（如：张三）"
            autoFocus
            style={{
              width: "100%",
              background: "var(--bg-card)",
              border: "1px solid var(--border-default)",
              borderRadius: 4,
              padding: "8px 12px",
              color: "var(--text-primary)",
              fontSize: 14,
              fontFamily: "var(--font-cn)",
              outline: "none",
            }}
          />
          <div
            style={{
              fontSize: 11,
              color: "var(--text-muted)",
              marginTop: 8,
              fontFamily: "var(--font-mono)",
            }}
          >
            {input.date} {input.time} · {input.gender === "male" ? "男" : "女"} ·{" "}
            {input.longitude}°E
          </div>
        </div>
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <button className="btn btn-secondary" onClick={onClose}>
            取消
          </button>
          <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
            {saving ? "保存中…" : "保存"}
          </button>
        </div>
      </div>
    </div>
  );
}
