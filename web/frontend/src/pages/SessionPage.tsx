import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { KairosLogo } from "../components/KairosLogo";
import { getChatAnalysis, sendChatMessage } from "../api/chatApi";
import { getConversation, listConversations } from "../api/conversationApi";
import type {
  ChatAnalysis,
  ChatState,
  ConversationSummary,
  Topic,
} from "../types/api";
import { ThemeSwitcher } from "../theme";

type UiMessage = {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  analysis_id: string | null;
  created_at?: string;
  followups?: string[];
  pending?: boolean;
  error?: boolean;
  feedback?: "like" | "dislike" | null;
};

type BirthInfo = {
  birth_date?: string | null;
  birth_time?: string | null;
  birth_place?: string | null;
  gender?: string | null;
  longitude?: number | null;
};

type StoredState = {
  conversationId: string | null;
  analysisId: string | null;
  adminMode: boolean;
  messages: UiMessage[];
  latestState: ChatState | null;
};

type LayoutState = {
  archiveCollapsed: boolean;
  railCollapsed: boolean;
};

const STORAGE_KEY = "bazibase-chat-session-v3";
const LAYOUT_KEY = "bazibase-panel-layout";
const ADMIN_CODE =
  (import.meta.env.VITE_ADMIN_UNLOCK_CODE as string | undefined) ?? "bypass";

function loadState(): StoredState {
  const adminFlag = window.localStorage.getItem("bazibase-admin-mode") === "1";
  const base: StoredState = {
    conversationId: null,
    analysisId: null,
    adminMode:
      adminFlag ||
      new URLSearchParams(window.location.search).get("admin") === "1",
    messages: [],
    latestState: null,
  };
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return base;
    const parsed = JSON.parse(raw) as Partial<StoredState>;
    return {
      ...base,
      conversationId: parsed.conversationId ?? null,
      analysisId: parsed.analysisId ?? null,
      adminMode: parsed.adminMode || adminFlag,
      messages: Array.isArray(parsed.messages) ? parsed.messages : [],
      latestState: parsed.latestState ?? null,
    };
  } catch {
    return base;
  }
}

function loadLayout(): LayoutState {
  try {
    const raw = localStorage.getItem(LAYOUT_KEY);
    if (!raw) return { archiveCollapsed: false, railCollapsed: false };
    const parsed = JSON.parse(raw) as Partial<LayoutState>;
    return {
      archiveCollapsed: parsed.archiveCollapsed === true,
      railCollapsed: parsed.railCollapsed === true,
    };
  } catch {
    return { archiveCollapsed: false, railCollapsed: false };
  }
}

function topicText(topic: Topic | string | null | undefined): string {
  if (!topic) return "未定";
  switch (topic) {
    case "career":
      return "事业";
    case "relationship":
      return "感情";
    case "wealth":
      return "财运";
    case "personality":
      return "性格";
    default:
      return "未定";
  }
}

function genderText(g: string | null | undefined): string {
  if (g === "male") return "男";
  if (g === "female") return "女";
  return "——";
}

function relativeTime(sqliteTs: string | null | undefined): string {
  if (!sqliteTs) return "——";
  const d = new Date(sqliteTs.replace(" ", "T") + "Z");
  if (Number.isNaN(d.getTime())) return "——";
  const now = Date.now();
  const diff = now - d.getTime();
  const min = Math.floor(diff / 60000);
  const hr = Math.floor(diff / 3600000);
  const day = Math.floor(diff / 86400000);
  if (min < 1) return "刚刚";
  if (min < 60) return `${min}分前`;
  if (hr < 24) return `${hr}时前`;
  if (day === 1) return "昨日";
  if (day < 7) return `${day}日前`;
  if (d.getFullYear() === new Date().getFullYear()) {
    return `${d.getMonth() + 1}月${d.getDate()}日`;
  }
  return `${d.getFullYear()}.${d.getMonth() + 1}.${d.getDate()}`;
}

function fieldLabel(field: string) {
  switch (field) {
    case "birth_date":
      return "生日";
    case "birth_time":
      return "时辰";
    case "birth_place":
      return "出生地";
    case "gender":
      return "性别";
    default:
      return field;
  }
}

export default function SessionPage() {
  const initial = useMemo(() => loadState(), []);
  const initialLayout = useMemo(() => loadLayout(), []);
  const location = useLocation();
  const initialMessage = (
    location.state as { initialMessage?: string } | null
  )?.initialMessage;

  const navigate = useNavigate();
  const { conversationId: urlConversationId } = useParams<{
    conversationId: string;
  }>();

  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [analysisId, setAnalysisId] = useState<string | null>(null);
  const [adminMode, setAdminMode] = useState(initial.adminMode);
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [latestState, setLatestState] = useState<ChatState | null>(null);
  const [birthInfo, setBirthInfo] = useState<BirthInfo | null>(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [analysis, setAnalysis] = useState<ChatAnalysis | null>(null);
  const [adminError, setAdminError] = useState<string | null>(null);
  const [showTrace, setShowTrace] = useState(false);
  const [loadingConv, setLoadingConv] = useState(false);
  const [mobilePanel, setMobilePanel] = useState<"archive" | "rail" | null>(
    null,
  );
  const [archiveCollapsed, setArchiveCollapsed] = useState(
    initialLayout.archiveCollapsed,
  );
  const [railCollapsed, setRailCollapsed] = useState(
    initialLayout.railCollapsed,
  );
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const sentRef = useRef(false);

  const refreshConversations = useCallback(() => {
    listConversations()
      .then(setConversations)
      .catch(() => {});
  }, []);

  useEffect(() => {
    refreshConversations();
  }, [refreshConversations]);

  useEffect(() => {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        conversationId,
        analysisId,
        adminMode,
        messages,
        latestState,
      } satisfies StoredState),
    );
  }, [analysisId, adminMode, conversationId, latestState, messages]);

  useEffect(() => {
    localStorage.setItem(
      LAYOUT_KEY,
      JSON.stringify({ archiveCollapsed, railCollapsed } satisfies LayoutState),
    );
  }, [archiveCollapsed, railCollapsed]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading]);

  useEffect(() => {
    if (!adminMode || !analysisId || !showTrace) {
      setAnalysis(null);
      setAdminError(null);
      return;
    }
    let cancelled = false;
    getChatAnalysis(analysisId)
      .then((data) => {
        if (!cancelled) {
          setAnalysis(data);
          setAdminError(null);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setAdminError(err instanceof Error ? err.message : "无法加载 trace");
          setAnalysis(null);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [adminMode, analysisId, showTrace]);

  const loadConversation = useCallback(async (id: string) => {
    setLoadingConv(true);
    try {
      const detail = await getConversation(id);
      setConversationId(id);
      setMessages(
        detail.messages.map((m) => ({
          id: m.id,
          role: m.role as UiMessage["role"],
          content: m.content,
          analysis_id: m.analysis_id,
          created_at: m.created_at,
        })),
      );
      const state = (detail.state ?? {}) as Record<string, unknown>;
      const birth = (state.birth_info ?? null) as BirthInfo | null;
      setBirthInfo(birth);
      const topic = (state.current_topic ?? null) as Topic;
      const lastAnalysis = (state.last_analysis_id ?? null) as string | null;
      setAnalysisId(lastAnalysis);
      setLatestState(
        topic
          ? {
              topic,
              needs_more_info: false,
              missing_fields: [],
              suggested_followups: [],
            }
          : null,
      );
    } catch {
      // conversation not found or error — silently ignore
    } finally {
      setLoadingConv(false);
    }
  }, []);

  const selectConversation = useCallback(
    (id: string) => {
      if (id === conversationId) return;
      setMobilePanel(null);
      navigate(`/session/${id}`);
    },
    [conversationId, navigate],
  );

  const startNew = useCallback(() => {
    setConversationId(null);
    setMessages([]);
    setAnalysisId(null);
    setLatestState(null);
    setBirthInfo(null);
    setMobilePanel(null);
    navigate("/session");
  }, [navigate]);

  const send = async (textInput?: string) => {
    const text = (textInput ?? input).trim();
    if (!text || loading) return;

    const userId = `local-${crypto.randomUUID()}`;
    const pendingId = `pending-${crypto.randomUUID()}`;
    setMessages((prev) => [
      ...prev,
      {
        id: userId,
        role: "user",
        content: text,
        analysis_id: null,
        created_at: new Date().toISOString(),
      },
      {
        id: pendingId,
        role: "assistant",
        content: "",
        analysis_id: null,
        created_at: new Date().toISOString(),
        pending: true,
      },
    ]);
    setInput("");
    setLoading(true);

    try {
      const res = await sendChatMessage(
        { conversation_id: conversationId ?? undefined, message: text },
        (chunk) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === pendingId
                ? { ...m, content: m.content + chunk, pending: false }
                : m,
            ),
          );
        },
      );
      setConversationId(res.conversation_id);
      navigate(`/session/${res.conversation_id}`, { replace: true });
      setAnalysisId(res.analysis_id);
      setLatestState(res.state);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === pendingId
            ? {
                ...m,
                analysis_id: res.analysis_id,
                followups: res.state.suggested_followups,
                pending: false,
              }
            : m,
        ),
      );
      refreshConversations();
    } catch (err) {
      const message = err instanceof Error ? err.message : "发送失败";
      setMessages((prev) =>
        prev.map((item) =>
          item.id === pendingId
            ? {
                ...item,
                content: `分析未能完成：${message}`,
                pending: false,
                error: true,
              }
            : item,
        ),
      );
    } finally {
      setLoading(false);
    }
  };

  // ── Receive initial message from landing page ──
  useEffect(() => {
    if (initialMessage && !sentRef.current) {
      sentRef.current = true;
      // Starting a new consultation from landing — clear any restored state first
      setConversationId(null);
      setMessages([]);
      setAnalysisId(null);
      setLatestState(null);
      setBirthInfo(null);
      void send(initialMessage);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialMessage]);

  // ── URL-driven conversation loading (direct visit / back / forward) ──
  useEffect(() => {
    if (!urlConversationId) return;
    if (urlConversationId === conversationId) return;
    void loadConversation(urlConversationId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [urlConversationId]);

  const onKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void send();
    }
  };

  const toggleAdmin = () => {
    const next = !adminMode;
    if (!next) {
      window.localStorage.removeItem("bazibase-admin-mode");
      setShowTrace(false);
      setAnalysis(null);
      setAdminError(null);
    } else {
      const code = window.prompt("输入管理员口令");
      if (code !== ADMIN_CODE) return;
      window.localStorage.setItem("bazibase-admin-mode", "1");
    }
    setAdminMode(next);
  };

  const needsMore = latestState?.needs_more_info ?? false;
  const missingLabels =
    latestState?.missing_fields.map(fieldLabel).join("、") ?? "";
  const railFollowups = latestState?.suggested_followups ?? [];
  const currentTopic = latestState?.topic ?? null;
  const currentConv = conversations.find((c) => c.id === conversationId);

  return (
    <div className="oracle">
      <div className="oracle__grain" aria-hidden />
      <div className="oracle__glow" aria-hidden />

      <header className="oracle-header">
        <div className="oracle-header__brand">
          <button
            type="button"
            className="oracle-header__nav oracle-header__nav--left"
            onClick={() =>
              setMobilePanel(mobilePanel === "archive" ? null : "archive")
            }
            aria-label="案卷"
          >
            案
          </button>
          <KairosLogo
            size={44}
            className="oracle-header__logo"
            role="button"
            onClick={() => navigate("/")}
          />
          <span className="oracle-header__mark">Kairos</span>
          <span className="oracle-header__rule" aria-hidden />
          <span className="oracle-header__sub">看清局势 · 把握时机</span>
          <button
            type="button"
            className="oracle-header__nav oracle-header__nav--right"
            onClick={() =>
              setMobilePanel(mobilePanel === "rail" ? null : "rail")
            }
            aria-label="案头"
          >
            注
          </button>
        </div>
        <div className="oracle-header__actions">
          <ThemeSwitcher />
        </div>
      </header>

      <main
        className={`oracle-body ${archiveCollapsed ? "is-archive-collapsed" : ""} ${railCollapsed ? "is-rail-collapsed" : ""}`}
      >
        {/* ── LEFT · 案卷 ── */}
        <aside
          className={`archive ${mobilePanel === "archive" ? "is-open" : ""}`}
        >
          <div className="archive__head">
            <button
              type="button"
              className={`archive__new-sm ${!conversationId ? "is-active" : ""}`}
              onClick={startNew}
            >
              ＋ 新对话
            </button>
            <button
              type="button"
              className="panel-collapse panel-collapse--archive"
              onClick={() => setArchiveCollapsed(true)}
              aria-label="收起案卷"
            >
              〈
            </button>
          </div>
          <div className="archive__list">
            {conversations.length === 0 && (
              <div className="archive__empty">
                <span>暂无对话</span>
                <span className="archive__empty-hint">
                  发送第一条消息开始
                </span>
              </div>
            )}
            {conversations.map((conv) => (
              <button
                key={conv.id}
                type="button"
                className={`slip ${
                  conv.id === conversationId ? "is-active" : ""
                }`}
                onClick={() => void selectConversation(conv.id)}
                disabled={loadingConv}
              >
                <div className="slip__edge" aria-hidden />
                <div className="slip__top">
                  <span
                    className={`slip__topic ${
                      conv.topic ? "has-topic" : "no-topic"
                    }`}
                  >
                    {conv.topic ? topicText(conv.topic) : "待定"}
                  </span>
                  <span className="slip__time">
                    {relativeTime(conv.last_message_at)}
                  </span>
                </div>
                <div className="slip__excerpt">
                  {conv.excerpt || "（无内容）"}
                </div>
                <div className="slip__foot">
                  <span className="slip__gender">
                    {genderText(conv.gender)}
                  </span>
                  <span className="slip__count">{conv.message_count}条</span>
                </div>
              </button>
            ))}
          </div>
        </aside>

        {/* ── MIDDLE · 问诊 ── */}
        <section className="oracle-chat">
          <div className="oracle-chat__scroll">
            {messages.length === 0 ? (
              <div className="oracle-empty oracle-empty--slim">
                <p className="oracle-empty__hint">有什么想了解的，直接问我。</p>
              </div>
            ) : (
              <div className="message-stream">
              {messages.map((message) => (
                <article
                  key={message.id}
                  className={`message message--${message.role} ${
                    message.pending ? "is-pending" : ""
                  } ${message.error ? "is-error" : ""}`}
                >
                  <div className="message__body">
                    {message.pending ? (
                      <span className="message__loading">
                        <span />
                        <span />
                        <span />
                      </span>
                    ) : (
                      message.content
                    )}
                  </div>
                  {!message.pending && message.analysis_id && (
                    <div className="message__meta">
                      <span className="message__id">
                        {message.analysis_id}
                      </span>
                    </div>
                  )}
                  {!message.pending && message.role === "assistant" && !message.error && (
                    <div className="message__actions">
                      <button
                        type="button"
                        className="msg-action"
                        aria-label="复制"
                        onClick={() => navigator.clipboard.writeText(message.content)}
                      >
                        <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
                          <rect x="5" y="5" width="9" height="9" rx="1.5" />
                          <path d="M11 5V3.5A1.5 1.5 0 0 0 9.5 2H3.5A1.5 1.5 0 0 0 2 3.5v6A1.5 1.5 0 0 0 3.5 11H5" />
                        </svg>
                      </button>
                      <button
                        type="button"
                        className={`msg-action ${message.feedback === "like" ? "is-active" : ""}`}
                        aria-label="有用"
                        onClick={() => setMessages(prev => prev.map(m =>
                          m.id === message.id
                            ? { ...m, feedback: m.feedback === "like" ? null : "like" }
                            : m
                        ))}
                      >
                        <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M5 7 L7.5 2 Q8 1 9 1.5 L9 5 H13.5 Q14.5 5 14 6.5 L12.5 11.5 Q12 13 11 13 H7 Q6 13 6 12 V8 Q6 7 5 7 Z" />
                          <path d="M5 7 H3.5 Q2 7 2 8 V12 Q2 13 3.5 13 H5" />
                        </svg>
                      </button>
                      <button
                        type="button"
                        className={`msg-action ${message.feedback === "dislike" ? "is-active" : ""}`}
                        aria-label="没用"
                        onClick={() => setMessages(prev => prev.map(m =>
                          m.id === message.id
                            ? { ...m, feedback: m.feedback === "dislike" ? null : "dislike" }
                            : m
                        ))}
                      >
                        <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M11 9 L8.5 14 Q8 15 7 14.5 L7 11 H2.5 Q1.5 11 2 9.5 L3.5 4.5 Q4 3 5 3 H9 Q10 3 10 4 V8 Q10 9 11 9 Z" />
                          <path d="M11 9 H12.5 Q14 9 14 8 V4 Q14 3 12.5 3 H11" />
                        </svg>
                      </button>
                    </div>
                  )}
                  {!message.pending &&
                    !message.error &&
                    message.followups &&
                    message.followups.length > 0 && (
                      <div className="message__followups">
                        {message.followups.map((f) => (
                          <button
                            key={f}
                            type="button"
                            className="followup-chip"
                            onClick={() => void send(f)}
                            disabled={loading}
                          >
                            {f}
                          </button>
                        ))}
                      </div>
                    )}
                </article>
              ))}
              <div ref={bottomRef} />
              </div>
            )}
          </div>

          <div className="composer">
            <div className="composer__wrap">
              <textarea
                className="composer__input"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={onKeyDown}
                placeholder="出生日期、地点、性别，以及你想了解的问题。"
                autoComplete="off"
                rows={1}
              />
              <button
                type="button"
                className="composer__send"
                onClick={() => void send()}
                disabled={loading || !input.trim()}
                aria-label="发送"
              >
                {loading ? (
                  <svg className="composer__spinner" width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
                    <circle cx="8" cy="8" r="6" strokeOpacity="0.25" />
                    <path d="M8 2a6 6 0 0 1 6 6" />
                  </svg>
                ) : (
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M2 8L14 2L8 14L7 9L2 8Z" />
                    <path d="M7 9L14 2" />
                  </svg>
                )}
              </button>
            </div>
          </div>
        </section>

        {/* ── RIGHT · 案头 ── */}
        <aside
          className={`insight-rail ${mobilePanel === "rail" ? "is-open" : ""}`}
        >
          <button
            type="button"
            className="panel-collapse panel-collapse--rail"
            onClick={() => setRailCollapsed(true)}
            aria-label="收起案头"
          >
            〉
          </button>

          <div className="rail-card">
            <div className="rail-card__label">当前话题</div>
            <div className="rail-card__value">
              {currentTopic || currentConv?.topic
                ? topicText(currentTopic ?? currentConv?.topic)
                : "——"}
            </div>
            {needsMore && missingLabels && (
              <div className="rail-card__alert">
                还需要 <strong>{missingLabels}</strong> 才能开始分析
              </div>
            )}
            {!needsMore && (currentTopic || currentConv?.topic) && (
              <div className="rail-card__meta">分析完成 · 可继续提问</div>
            )}
          </div>

          {birthInfo &&
            (birthInfo.birth_date ||
              birthInfo.birth_time ||
              birthInfo.birth_place) && (
              <div className="rail-card rail-card--birth">
                <div className="rail-card__label">生辰</div>
                <dl className="birth-grid">
                  {birthInfo.birth_date && (
                    <div className="birth-row">
                      <dt>日</dt>
                      <dd>{birthInfo.birth_date}</dd>
                    </div>
                  )}
                  {birthInfo.birth_time && (
                    <div className="birth-row">
                      <dt>时</dt>
                      <dd>{birthInfo.birth_time}</dd>
                    </div>
                  )}
                  {birthInfo.birth_place && (
                    <div className="birth-row">
                      <dt>地</dt>
                      <dd>{birthInfo.birth_place}</dd>
                    </div>
                  )}
                  <div className="birth-row">
                    <dt>造</dt>
                    <dd>{genderText(birthInfo.gender)}</dd>
                  </div>
                </dl>
              </div>
            )}

          {railFollowups.length > 0 && (
            <div className="rail-card">
              <div className="rail-card__label">继续了解</div>
              <div className="rail-chips">
                {railFollowups.map((f) => (
                  <button
                    key={f}
                    type="button"
                    className="rail-chip"
                    onClick={() => void send(f)}
                    disabled={loading}
                  >
                    {f}
                  </button>
                ))}
              </div>
            </div>
          )}
        </aside>
      </main>

      {/* ── Desktop reopen tabs (shown when a panel is collapsed) ── */}
      <button
        type="button"
        className={`edge-tab edge-tab--left ${archiveCollapsed ? "is-visible" : ""}`}
        onClick={() => setArchiveCollapsed(false)}
        aria-label="展开案卷"
      >
        案〉
      </button>
      <button
        type="button"
        className={`edge-tab edge-tab--right ${railCollapsed ? "is-visible" : ""}`}
        onClick={() => setRailCollapsed(false)}
        aria-label="展开案头"
      >
        〈注
      </button>

      {mobilePanel && (
        <div
          className="oracle__scrim"
          onClick={() => setMobilePanel(null)}
          aria-hidden
        />
      )}
    </div>
  );
}
