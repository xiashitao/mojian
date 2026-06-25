import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { sendChatMessage } from "../api/chatApi";
import { getConversation } from "../api/conversationApi";
import type { ChatState, Topic } from "../types/api";
import type { BirthInfo, MessageFeedback, UiMessage } from "../types/session";
import { useArchiveCollapsed } from "./useArchiveCollapsed";
import { useConversations } from "./useConversations";

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

  const { conversations, refresh: refreshConversations } = useConversations();
  const [archiveCollapsed, setArchiveCollapsed] = useArchiveCollapsed();

  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [latestState, setLatestState] = useState<ChatState | null>(null);
  const [birthInfo, setBirthInfo] = useState<BirthInfo | null>(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingConv, setLoadingConv] = useState(false);
  const [mobilePanel, setMobilePanel] = useState<"archive" | null>(null);

  const bottomRef = useRef<HTMLDivElement | null>(null);
  const sentRef = useRef(false);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading]);

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
      setMobilePanel(null);
      navigate(`/session/${id}`);
    },
    [conversationId, navigate],
  );

  const startNew = useCallback(() => {
    setConversationId(null);
    setMessages([]);
    setLatestState(null);
    setBirthInfo(null);
    setMobilePanel(null);
    navigate("/session");
  }, [navigate]);

  const goHome = useCallback(() => navigate("/"), [navigate]);

  const send = useCallback(
    async (textInput?: string) => {
      const text = (textInput ?? input).trim();
      if (!text || loading) return;

      const userId = `local-${crypto.randomUUID()}`;
      const pendingId = `pending-${crypto.randomUUID()}`;
      const now = new Date().toISOString();
      setMessages((prev) => [
        ...prev,
        { id: userId, role: "user", content: text, analysis_id: null, created_at: now },
        { id: pendingId, role: "assistant", content: "", analysis_id: null, created_at: now, pending: true },
      ]);
      setInput("");
      setLoading(true);

      try {
        const res = await sendChatMessage(
          { conversation_id: conversationId ?? undefined, message: text },
          (chunk) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === pendingId ? { ...m, content: m.content + chunk, pending: false } : m,
              ),
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
        const message = err instanceof Error ? err.message : "发送失败";
        setMessages((prev) =>
          prev.map((m) =>
            m.id === pendingId
              ? { ...m, content: `分析未能完成：${message}`, pending: false, error: true }
              : m,
          ),
        );
      } finally {
        setLoading(false);
      }
    },
    [conversationId, input, loading, navigate, refreshConversations],
  );

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
    birthInfo,
    currentTopic,
    currentConv,
    archiveCollapsed,
    setArchiveCollapsed,
    mobilePanel,
    setMobilePanel,
    bottomRef,
    send,
    startNew,
    selectConversation,
    setMessageFeedback,
    goHome,
  } as const;
}
