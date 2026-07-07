import { useCallback, useEffect, useRef, useState, type KeyboardEvent } from "react";
import { ApiError } from "../../api/client";
import { fetchAsrEnabled, recognizeVoice } from "../../api/asrApi";
import {
  blobToBase64,
  startRecording,
  type VoiceRecorder,
} from "../../utils/voiceRecorder";
import { ComposerHints } from "./ComposerHints";
import { TonePopover, toneLabel, type ToneId } from "./TonePopover";

const PLACEHOLDER_FULL = "出生日期、地点、性别，以及你想了解的问题。";
const PLACEHOLDER_MOBILE = "出生信息和你想问的";
const MOBILE_QUERY = "(max-width: 640px)";

type MicState = "idle" | "recording" | "busy";

export interface ComposerProps {
  value: string;
  loading: boolean;
  tone: ToneId;
  onToneChange: (tone: ToneId) => void;
  onChange: (value: string) => void;
  onSend: () => void;
  onStop: () => void;
}

/** Bottom composer: textarea, typing indicator, tone selector, voice input and send / stop button. */
export function Composer({ value, loading, tone, onToneChange, onChange, onSend, onStop }: ComposerProps) {
  const [toneOpen, setToneOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(
    () => typeof window !== "undefined" && window.matchMedia(MOBILE_QUERY).matches,
  );

  // ── 语音输入 ──────────────────────────────────────
  const [asrEnabled, setAsrEnabled] = useState(false);
  const [micState, setMicState] = useState<MicState>("idle");
  const [micError, setMicError] = useState<string | null>(null);
  const recorderRef = useRef<VoiceRecorder | null>(null);
  // 识别结果要接在「当时」的输入后面,不能用闭包里可能过期的 value。
  const valueRef = useRef(value);
  valueRef.current = value;

  useEffect(() => {
    // 服务端没配 ASR 密钥就不渲染麦克风,避免点了才报错。
    fetchAsrEnabled()
      .then((r) => setAsrEnabled(r.enabled))
      .catch(() => setAsrEnabled(false));
  }, []);

  useEffect(() => {
    if (!micError) return;
    const id = window.setTimeout(() => setMicError(null), 4000);
    return () => window.clearTimeout(id);
  }, [micError]);

  // 组件卸载时释放麦克风。
  useEffect(() => () => recorderRef.current?.cancel(), []);

  const stopAndRecognize = useCallback(async () => {
    const recorder = recorderRef.current;
    if (!recorder) return;
    recorderRef.current = null;
    setMicState("busy");
    try {
      const blob = await recorder.stop();
      if (!blob) {
        setMicState("idle");
        return;
      }
      const { text } = await recognizeVoice(await blobToBase64(blob));
      const prev = valueRef.current;
      onChange(prev ? `${prev}${text}` : text);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setMicError("请先登录再使用语音输入");
      } else {
        setMicError(err instanceof ApiError ? err.message : "语音识别失败，请重试");
      }
    } finally {
      setMicState("idle");
    }
  }, [onChange]);

  // 录满上限自动走停止流程;用 ref 避免闭包拿到旧的回调。
  const stopRef = useRef(stopAndRecognize);
  stopRef.current = stopAndRecognize;

  const toggleMic = useCallback(async () => {
    if (micState === "busy") return;
    if (micState === "recording") {
      void stopAndRecognize();
      return;
    }
    try {
      recorderRef.current = await startRecording(() => void stopRef.current());
      setMicState("recording");
    } catch {
      setMicError("无法访问麦克风，请检查浏览器权限");
    }
  }, [micState, stopAndRecognize]);

  useEffect(() => {
    const mq = window.matchMedia(MOBILE_QUERY);
    const onChange = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      onSend();
    }
  };

  const toggleTone = () => setToneOpen((open) => !open);

  return (
    <div className="composer">
      <div className="composer__wrap">
        {/* Above the box: typing indicator while analysing, rotating hints (PC) when idle. */}
        {loading ? (
          <div className="composer__typing">
            <span className="composer__typing-dots">
              <span />
              <span />
              <span />
            </span>
            分析中
          </div>
        ) : (
          <ComposerHints />
        )}

        {micError && <div className="composer__mic-error">{micError}</div>}

        <div className="composer__box">
          {/* Mobile-only: a plus that rotates 45° and opens the tone popover. */}
          <button
            type="button"
            className={"composer__plus" + (toneOpen ? " is-open" : "")}
            onClick={toggleTone}
            aria-label="更多选项"
            aria-expanded={toneOpen}
          >
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round">
              <path d="M9 3.5v11M3.5 9h11" />
            </svg>
          </button>

          <textarea
            className="composer__input"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              micState === "recording"
                ? "正在录音，再点一下麦克风结束…"
                : isMobile
                  ? PLACEHOLDER_MOBILE
                  : PLACEHOLDER_FULL
            }
            autoComplete="off"
            rows={1}
          />

          <div className="composer__toolbar">
            {/* PC-only: labelled tone button. */}
            <button
              type="button"
              className={"composer__tool" + (toneOpen ? " is-open" : "")}
              onClick={toggleTone}
              aria-expanded={toneOpen}
            >
              <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
                <path d="M2.5 4.5h11v6H6l-2.5 2v-2h-1z" />
              </svg>
              <span>{toneLabel(tone)}</span>
            </button>

            {asrEnabled && (
              <button
                type="button"
                className={
                  "composer__mic" +
                  (micState === "recording" ? " is-recording" : "") +
                  (micState === "busy" ? " is-busy" : "")
                }
                onClick={() => void toggleMic()}
                disabled={loading || micState === "busy"}
                aria-label={micState === "recording" ? "结束录音" : "语音输入"}
                title={micState === "recording" ? "结束录音" : "语音输入"}
              >
                {micState === "busy" ? (
                  <svg className="composer__mic-spin" width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round">
                    <path d="M8 1.5A6.5 6.5 0 1 1 1.5 8" />
                  </svg>
                ) : (
                  <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="5.75" y="1.5" width="4.5" height="8" rx="2.25" />
                    <path d="M3.5 7.5a4.5 4.5 0 0 0 9 0" />
                    <path d="M8 12v2.5" />
                  </svg>
                )}
              </button>
            )}

            {loading ? (
              <button
                type="button"
                className="composer__send composer__send--stop"
                onClick={onStop}
                aria-label="停止"
                title="停止（Esc）"
              >
                <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
                  <rect x="3.5" y="3.5" width="9" height="9" rx="1.5" />
                </svg>
              </button>
            ) : (
              <button
                type="button"
                className="composer__send"
                onClick={onSend}
                disabled={!value.trim()}
                aria-label="发送"
              >
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M2 8L14 2L8 14L7 9L2 8Z" />
                  <path d="M7 9L14 2" />
                </svg>
              </button>
            )}
          </div>
        </div>

        {toneOpen && (
          <TonePopover
            selected={tone}
            onSelect={onToneChange}
            onClose={() => setToneOpen(false)}
          />
        )}
      </div>
    </div>
  );
}
