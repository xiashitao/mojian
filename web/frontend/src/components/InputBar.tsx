import type { BirthInput } from "../types/api";

interface InputBarProps {
  onSubmit: (input: BirthInput) => void;
  loading: boolean;
  onSave: () => void;
  canSave: boolean;
}

export function InputBar({ onSubmit, loading, onSave, canSave }: InputBarProps) {
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const form = new FormData(e.target as HTMLFormElement);
    onSubmit({
      date: form.get("date") as string,
      time: form.get("time") as string,
      longitude: parseFloat(form.get("longitude") as string),
      gender: form.get("gender") as "male" | "female",
      tz_offset_hours: parseFloat(form.get("tz") as string),
      apply_solar_time_correction: true,
    });
  };

  return (
    <form className="input-bar" onSubmit={handleSubmit}>
      <div className="input-field">
        <label>DATE</label>
        <input name="date" type="date" defaultValue="1985-03-15" />
      </div>
      <div className="input-field">
        <label>TIME</label>
        <input name="time" type="time" defaultValue="10:30" />
      </div>
      <div className="input-field">
        <label>LON</label>
        <input name="longitude" type="number" step="0.1" defaultValue="116.4" />
      </div>
      <div className="input-field">
        <label>GENDER</label>
        <select name="gender" defaultValue="male">
          <option value="male">男</option>
          <option value="female">女</option>
        </select>
      </div>
      <div className="input-field">
        <label>TZ OFFSET</label>
        <input name="tz" type="number" step="0.5" defaultValue="8" />
      </div>
      <button type="submit" className="btn btn-primary" disabled={loading}>
        {loading ? "排盘中…" : "排 盘"}
      </button>
      <button
        type="button"
        className="btn btn-secondary"
        onClick={onSave}
        disabled={!canSave}
      >
        保存命例
      </button>
    </form>
  );
}
