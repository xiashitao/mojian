import { useState } from "react";

/** 命盘主体:这套八字是谁的。与后端 Subject 枚举一一对应。 */
export type Subject = "self" | "spouse" | "child" | "parent" | "other";

const SUBJECT_OPTIONS: { value: Subject; label: string; hint: string }[] = [
  { value: "self", label: "我自己", hint: "用户本人" },
  { value: "spouse", label: "配偶", hint: "老公 / 老婆 / 另一半" },
  { value: "child", label: "子女", hint: "儿子 / 女儿 / 孩子" },
  { value: "parent", label: "父母", hint: "爸爸 / 妈妈" },
  { value: "other", label: "其他人", hint: "朋友 / 合伙人 / 亲属" },
];

export interface SubjectConfirmDialogProps {
  /** 后端抽到的、待确认主体的八字信息(用于展示)。 */
  birthInfo: Record<string, unknown> | null;
  /** 用户取消(关闭对话框)。父组件应回滚那条 pending 消息。 */
  onCancel: () => void;
  /** 用户确认主体。父组件带这个 subject 重发原消息。 */
  onConfirm: (subject: Subject) => void;
}

/**
 * 主体确认对话框:后端从消息里抽到了完整的生辰,但无法判断是「谁的」
 * (subject=unknown)。前端弹这个极简对话框让用户一键选择,选完后带
 * subject 重发同一条消息,后端据此排盘。
 *
 * 设计:只问「这是哪位的?」,不重报八字(八字已从对话抽出)。
 * 移动端友好:纵向单选 + 大点击区 + 顶部键盘避让(复用 auth-modal 样式)。
 */
export function SubjectConfirmDialog({ birthInfo, onCancel, onConfirm }: SubjectConfirmDialogProps) {
  const [picked, setPicked] = useState<Subject>("self");

  // 把抽到的八字格式化成可读的一行,让用户核对。
  const birthLine = birthInfo
    ? [
        birthInfo.birth_date as string | undefined,
        birthInfo.birth_time as string | undefined,
        birthInfo.birth_place as string | undefined,
        birthInfo.gender === "male" ? "男" : birthInfo.gender === "female" ? "女" : undefined,
      ]
        .filter(Boolean)
        .join(" · ")
    : "";

  return (
    <div className="auth-scrim" onClick={onCancel}>
      <div
        className="auth-modal subject-modal"
        role="dialog"
        aria-modal="true"
        aria-label="确认命盘主体"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="auth-modal__title">这是哪位的生辰?</h3>
        {birthLine && <p className="subject-modal__birth">已识别:{birthLine}</p>}
        <p className="subject-modal__hint">选好后会基于这位的八字来分析。</p>

        <div className="subject-modal__options" role="radiogroup">
          {SUBJECT_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              role="radio"
              aria-checked={picked === opt.value}
              className={`subject-option ${picked === opt.value ? "is-selected" : ""}`}
              onClick={() => setPicked(opt.value)}
            >
              <span className="subject-option__label">{opt.label}</span>
              <span className="subject-option__hint">{opt.hint}</span>
            </button>
          ))}
        </div>

        <div className="subject-modal__actions">
          <button type="button" className="auth-linkbtn" onClick={onCancel}>
            取消
          </button>
          <button
            type="button"
            className="auth-submit"
            onClick={() => onConfirm(picked)}
          >
            确认并分析
          </button>
        </div>
      </div>
    </div>
  );
}
