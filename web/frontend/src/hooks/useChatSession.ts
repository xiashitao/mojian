import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { AuthRequiredError, sendChatMessage } from "../api/chatApi";
import { getConversation, postFeedback } from "../api/conversationApi";
import { useAuth } from "../auth";
import { uuid } from "../utils/anonId";
import type { ChatState, Topic } from "../types/api";
import type {
  BirthInfo,
  ChartData,
  MessageFeedback,
  UiMessage,
} from "../types/session";
import { useArchiveCollapsed } from "./useArchiveCollapsed";
import { useConversations } from "./useConversations";
import { DEFAULT_TONE, type ToneId } from "../components/session/TonePopover";

/** Pull persisted chart + follow-ups + feedback out of a stored message's metadata. */
function parseMeta(metadataJson?: string): {
  chart?: ChartData;
  followups?: string[];
  feedback?: MessageFeedback | null;
} {
  if (!metadataJson) return {};
  try {
    const meta = JSON.parse(metadataJson) as {
      chart?: ChartData;
      suggested_followups?: string[];
      feedback?: MessageFeedback | null;
    };
    return {
      chart: meta.chart,
      followups: meta.suggested_followups,
      feedback: meta.feedback ?? null,
    };
  } catch {
    return {};
  }
}

/** Owns chat-session state and side effects, composed from smaller hooks. */
export function useChatSession() {
  const location = useLocation();
  const navigate = useNavigate();
  const { conversationId: urlConversationId } = useParams<{
    conversationId: string;
  }>();
  const initialMessage = (
    location.state as { initialMessage?: string } | null
  )?.initialMessage;

  const { user, loading: authLoading } = useAuth();
  const { conversations, refresh: refreshConversations } = useConversations();
  const [archiveCollapsed, setArchiveCollapsed] = useArchiveCollapsed();
  const [authPrompt, setAuthPrompt] = useState(false);

  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [latestState, setLatestState] = useState<ChatState | null>(null);
  const [birthInfo, setBirthInfo] = useState<BirthInfo | null>(null);
  const [input, setInput] = useState("");
  const [tone, setTone] = useState<ToneId>(DEFAULT_TONE);
  const [loading, setLoading] = useState(false);
  const [loadingConv, setLoadingConv] = useState(false);
  const [mobilePanel, setMobilePanel] = useState<"archive" | null>(null);
  // 主体确认对话框:后端返回 needs_subject_confirmation 时,挂起的消息文本 +
  // 抽到的八字。用户选完主体后,带 subject 重发 text。
  const [subjectConfirm, setSubjectConfirm] = useState<{
    text: string;
    birthInfo: Record<string, unknown> | null;
  } | null>(null);

  const bottomRef = useRef<HTMLDivElement | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  // 智能跟随:流式输出时每个 token 都会更新 messages,若无条件滚到底,
  // 用户往上翻会被不断顶回去。规则:在底部(阈值内)才跟随;往上滚就暂停;
  // 滚回底部自动恢复;自己发新消息时强制恢复。
  const followRef = useRef(true);
  const sentRef = useRef(false);
  const abortRef = useRef<AbortController | null>(null);
  const pendingPairRef = useRef<{ userId: string; pendingId: string; text: string } | null>(null);

  const handleScroll = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    const distance = el.scrollHeight - el.scrollTop - el.clientHeight;
    followRef.current = distance < 80;
  }, []);

  useEffect(() => {
    if (!followRef.current) return;
    // 即时滚动(非 smooth):smooth 的动画期间滚动位置不在底部,
    // 会让 handleScroll 误判"用户离开了底部"而错误暂停跟随。
    bottomRef.current?.scrollIntoView({ block: "end" });
  }, [messages, loading]);

  const loadConversation = useCallback(async (id: string) => {
    setLoadingConv(true);
    try {
      const detail = await getConversation(id);
      setConversationId(id);
      setMessages(
        detail.messages.map((m) => {
          const meta = parseMeta(m.metadata_json);
          return {
            id: m.id,
            role: m.role as UiMessage["role"],
            content: m.content,
            analysis_id: m.analysis_id,
            created_at: m.created_at,
            chart: meta.chart,
            followups: meta.followups,
            feedback: meta.feedback,
          };
        }),
      );
      const state = (detail.state ?? {}) as Record<string, unknown>;
      setBirthInfo((state.birth_info ?? null) as BirthInfo | null);
      const topic = (state.current_topic ?? null) as Topic;
      setLatestState(
        topic
          ? { topic, needs_more_info: false, missing_fields: [], suggested_followups: [] }
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
      // 注意:不要在这里 setMobilePanel(null)。mobilePanel 是移动端抽屉的开关,
      // 在移动端切换会话后强行收起抽屉,会让用户看不到切换结果——这是 bug。
      // 抽屉的关闭应交给遮罩点击 / 收起按钮 / 汉堡按钮,由用户主动触发。
      navigate(`/session/${id}`);
    },
    [conversationId, navigate],
  );

  const startNew = useCallback(() => {
    setConversationId(null);
    setMessages([]);
    setLatestState(null);
    setBirthInfo(null);
    // 新建后收起移动端抽屉:点新建的意图就是马上开始输入,
    // 抽屉留着反而挡住空白对话(桌面端无抽屉,置 null 无副作用)。
    setMobilePanel(null);
    navigate("/session");
  }, [navigate]);

  const goHome = useCallback(() => navigate("/"), [navigate]);

  const send = useCallback(
    async (textInput?: string, subjectOverride?: string) => {
      const text = (textInput ?? input).trim();
      if (!text || loading) return;

      // Login required: guide anonymous users to sign in instead of sending.
      if (!authLoading && !user) {
        setInput((cur) => cur || text);
        setAuthPrompt(true);
        return;
      }

      followRef.current = true; // 自己发消息 = 明确想看最新回复,恢复跟随
      const userId = `local-${uuid()}`;
      const pendingId = `pending-${uuid()}`;
      const now = new Date().toISOString();
      const controller = new AbortController();
      abortRef.current = controller;
      pendingPairRef.current = { userId, pendingId, text };
      setMessages((prev) => [
        ...prev,
        { id: userId, role: "user", content: text, analysis_id: null, created_at: now },
        { id: pendingId, role: "assistant", content: "", analysis_id: null, created_at: now, pending: true },
      ]);
      setInput("");
      setLoading(true);

      try {
        const res = await sendChatMessage(
          { conversation_id: conversationId ?? undefined, message: text, tone, subject: subjectOverride },
          (chunk) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === pendingId ? { ...m, content: m.content + chunk, pending: false } : m,
              ),
            );
          },
          controller.signal,
          (chart) => {
            setMessages((prev) =>
              prev.map((m) => (m.id === pendingId ? { ...m, chart } : m)),
            );
          },
          (birthInfo) => {
            // 后端要求确认主体:回滚这条消息(避免"半截"消息留在对话流),
            // 弹出主体确认对话框。用户选完后会带 subject 重发。
            setMessages((prev) =>
              prev.filter((m) => m.id !== userId && m.id !== pendingId),
            );
            setInput(text);  // 恢复输入框,让用户看到原消息
            setSubjectConfirm({ text, birthInfo });
          },
        );
        setConversationId(res.conversation_id);
        navigate(`/session/${res.conversation_id}`, { replace: true });
        setLatestState(res.state);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === pendingId
              ? { ...m, analysis_id: res.analysis_id, followups: res.state.suggested_followups, pending: false }
              : m,
          ),
        );
        refreshConversations();
      } catch (err) {
        // Aborted by the user (stop button / Esc) — revert is handled in stop().
        if (controller.signal.aborted) return;
        // Session expired / not authenticated — drop the optimistic pair,
        // restore the text, and guide the user to log in.
        if (err instanceof AuthRequiredError) {
          setMessages((prev) =>
            prev.filter((m) => m.id !== userId && m.id !== pendingId),
          );
          setInput((cur) => cur || text);
          setAuthPrompt(true);
          return;
        }
        const message = err instanceof Error ? err.message : "发送失败";
        setMessages((prev) =>
          prev.map((m) =>
            m.id === pendingId
              ? { ...m, content: `分析未能完成：${message}`, pending: false, error: true }
              : m,
          ),
        );
      } finally {
        if (abortRef.current === controller) abortRef.current = null;
        setLoading(false);
      }
    },
    [authLoading, conversationId, input, loading, navigate, refreshConversations, tone, user],
  );

  // 用户在主体确认对话框里选了主体 → 带该 subject 重发原消息。
  const confirmSubject = useCallback(
    (subject: string) => {
      const text = subjectConfirm?.text;
      setSubjectConfirm(null);
      setInput("");
      if (text) void send(text, subject);
    },
    [subjectConfirm, send],
  );

  // 用户取消主体确认 → 关闭对话框(消息已在 onSubjectConfirmation 里回滚)。
  const cancelSubjectConfirm = useCallback(() => {
    setSubjectConfirm(null);
  }, []);

  const stop = useCallback(() => {
    const controller = abortRef.current;
    const pair = pendingPairRef.current;
    if (!controller || !pair) return;
    controller.abort();
    abortRef.current = null;
    // Revert: drop the just-sent user message and its pending reply, restore the text.
    setMessages((prev) =>
      prev.filter((m) => m.id !== pair.userId && m.id !== pair.pendingId),
    );
    setInput((current) => current || pair.text);
    setLoading(false);
  }, []);

  // Press Esc while a reply is streaming to interrupt and revert.
  useEffect(() => {
    if (!loading) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") stop();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [loading, stop]);

  const setMessageFeedback = useCallback(
    (id: string, feedback: MessageFeedback) => {
      const target = messages.find((m) => m.id === id);
      if (!target) return;
      const next = target.feedback === feedback ? null : feedback; // 再点一次=撤销
      setMessages((prev) =>
        prev.map((m) => (m.id === id ? { ...m, feedback: next } : m)),
      );
      // 持久化(按 analysis_id,后端做归属校验)。乐观更新,失败静默——
      // 反馈是增强功能,不值得为它打断用户;运营侧看到的是落库成功的那部分。
      if (target.analysis_id) {
        void postFeedback(target.analysis_id, next).catch(() => {});
      }
    },
    [messages],
  );

  // Receive an initial message handed off from the landing page.
  useEffect(() => {
    if (!initialMessage || sentRef.current) return;
    sentRef.current = true;
    setConversationId(null);
    setMessages([]);
    setLatestState(null);
    setBirthInfo(null);
    void send(initialMessage);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialMessage]);

  // URL-driven conversation loading (direct visit / back / forward).
  useEffect(() => {
    if (!urlConversationId || urlConversationId === conversationId) return;
    void loadConversation(urlConversationId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [urlConversationId]);

  const currentTopic = latestState?.topic ?? null;
  const currentConv = conversations.find((c) => c.id === conversationId);

  return {
    conversations,
    conversationId,
    messages,
    loading,
    loadingConv,
    input,
    setInput,
    tone,
    setTone,
    birthInfo,
    currentTopic,
    currentConv,
    archiveCollapsed,
    setArchiveCollapsed,
    mobilePanel,
    setMobilePanel,
    bottomRef,
    scrollRef,
    handleScroll,
    send,
    stop,
    startNew,
    selectConversation,
    setMessageFeedback,
    goHome,
    authPrompt,
    closeAuthPrompt: () => setAuthPrompt(false),
    subjectConfirm,
    confirmSubject,
    cancelSubjectConfirm,
  } as const;
}
