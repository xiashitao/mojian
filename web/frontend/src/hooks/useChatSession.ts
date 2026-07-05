import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { AuthRequiredError, sendChatMessage } from "../api/chatApi";
import { getConversation } from "../api/conversationApi";
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

/** Pull persisted chart + follow-ups out of a stored message's metadata. */
function parseMeta(metadataJson?: string): {
  chart?: ChartData;
  followups?: string[];
} {
  if (!metadataJson) return {};
  try {
    const meta = JSON.parse(metadataJson) as {
      chart?: ChartData;
      suggested_followups?: string[];
    };
    return { chart: meta.chart, followups: meta.suggested_followups };
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

  const bottomRef = useRef<HTMLDivElement | null>(null);
  const sentRef = useRef(false);
  const abortRef = useRef<AbortController | null>(null);
  const pendingPairRef = useRef<{ userId: string; pendingId: string; text: string } | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
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
    // 同上:不在新建会话时关闭移动端抽屉,否则面板会立刻收起。
    navigate("/session");
  }, [navigate]);

  const goHome = useCallback(() => navigate("/"), [navigate]);

  const send = useCallback(
    async (textInput?: string) => {
      const text = (textInput ?? input).trim();
      if (!text || loading) return;

      // Login required: guide anonymous users to sign in instead of sending.
      if (!authLoading && !user) {
        setInput((cur) => cur || text);
        setAuthPrompt(true);
        return;
      }

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
          { conversation_id: conversationId ?? undefined, message: text, tone },
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

  const setMessageFeedback = useCallback((id: string, feedback: MessageFeedback) => {
    setMessages((prev) =>
      prev.map((m) =>
        m.id === id ? { ...m, feedback: m.feedback === feedback ? null : feedback } : m,
      ),
    );
  }, []);

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
    send,
    stop,
    startNew,
    selectConversation,
    setMessageFeedback,
    goHome,
    authPrompt,
    closeAuthPrompt: () => setAuthPrompt(false),
  } as const;
}
