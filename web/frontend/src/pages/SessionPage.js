import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import logo from "../assets/logo.png";
import { getChatAnalysis, sendChatMessage } from "../api/chatApi";
import { getConversation, listConversations } from "../api/conversationApi";
import { ThemeSwitcher } from "../theme";
const STORAGE_KEY = "bazibase-chat-session-v3";
const LAYOUT_KEY = "bazibase-panel-layout";
const ADMIN_CODE = import.meta.env.VITE_ADMIN_UNLOCK_CODE ?? "bypass";
function loadState() {
    const adminFlag = window.localStorage.getItem("bazibase-admin-mode") === "1";
    const base = {
        conversationId: null,
        analysisId: null,
        adminMode: adminFlag ||
            new URLSearchParams(window.location.search).get("admin") === "1",
        messages: [],
        latestState: null,
    };
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (!raw)
            return base;
        const parsed = JSON.parse(raw);
        return {
            ...base,
            conversationId: parsed.conversationId ?? null,
            analysisId: parsed.analysisId ?? null,
            adminMode: parsed.adminMode || adminFlag,
            messages: Array.isArray(parsed.messages) ? parsed.messages : [],
            latestState: parsed.latestState ?? null,
        };
    }
    catch {
        return base;
    }
}
function loadLayout() {
    try {
        const raw = localStorage.getItem(LAYOUT_KEY);
        if (!raw)
            return { archiveCollapsed: false, railCollapsed: false };
        const parsed = JSON.parse(raw);
        return {
            archiveCollapsed: parsed.archiveCollapsed === true,
            railCollapsed: parsed.railCollapsed === true,
        };
    }
    catch {
        return { archiveCollapsed: false, railCollapsed: false };
    }
}
function topicText(topic) {
    if (!topic)
        return "未定";
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
function genderText(g) {
    if (g === "male")
        return "乾造";
    if (g === "female")
        return "坤造";
    return "——";
}
function relativeTime(sqliteTs) {
    if (!sqliteTs)
        return "——";
    const d = new Date(sqliteTs.replace(" ", "T") + "Z");
    if (Number.isNaN(d.getTime()))
        return "——";
    const now = Date.now();
    const diff = now - d.getTime();
    const min = Math.floor(diff / 60000);
    const hr = Math.floor(diff / 3600000);
    const day = Math.floor(diff / 86400000);
    if (min < 1)
        return "方才";
    if (min < 60)
        return `${min}分前`;
    if (hr < 24)
        return `${hr}时前`;
    if (day === 1)
        return "昨日";
    if (day < 7)
        return `${day}日前`;
    if (d.getFullYear() === new Date().getFullYear()) {
        return `${d.getMonth() + 1}月${d.getDate()}日`;
    }
    return `${d.getFullYear()}.${d.getMonth() + 1}.${d.getDate()}`;
}
function fieldLabel(field) {
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
    const initialMessage = location.state?.initialMessage;
    const navigate = useNavigate();
    const { conversationId: urlConversationId } = useParams();
    const [conversations, setConversations] = useState([]);
    const [conversationId, setConversationId] = useState(null);
    const [analysisId, setAnalysisId] = useState(null);
    const [adminMode, setAdminMode] = useState(initial.adminMode);
    const [messages, setMessages] = useState([]);
    const [latestState, setLatestState] = useState(null);
    const [birthInfo, setBirthInfo] = useState(null);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [analysis, setAnalysis] = useState(null);
    const [adminError, setAdminError] = useState(null);
    const [showTrace, setShowTrace] = useState(false);
    const [loadingConv, setLoadingConv] = useState(false);
    const [mobilePanel, setMobilePanel] = useState(null);
    const [archiveCollapsed, setArchiveCollapsed] = useState(initialLayout.archiveCollapsed);
    const [railCollapsed, setRailCollapsed] = useState(initialLayout.railCollapsed);
    const bottomRef = useRef(null);
    const sentRef = useRef(false);
    const refreshConversations = useCallback(() => {
        listConversations()
            .then(setConversations)
            .catch(() => { });
    }, []);
    useEffect(() => {
        refreshConversations();
    }, [refreshConversations]);
    useEffect(() => {
        localStorage.setItem(STORAGE_KEY, JSON.stringify({
            conversationId,
            analysisId,
            adminMode,
            messages,
            latestState,
        }));
    }, [analysisId, adminMode, conversationId, latestState, messages]);
    useEffect(() => {
        localStorage.setItem(LAYOUT_KEY, JSON.stringify({ archiveCollapsed, railCollapsed }));
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
    const loadConversation = useCallback(async (id) => {
        setLoadingConv(true);
        try {
            const detail = await getConversation(id);
            setConversationId(id);
            setMessages(detail.messages.map((m) => ({
                id: m.id,
                role: m.role,
                content: m.content,
                analysis_id: m.analysis_id,
                created_at: m.created_at,
            })));
            const state = (detail.state ?? {});
            const birth = (state.birth_info ?? null);
            setBirthInfo(birth);
            const topic = (state.current_topic ?? null);
            const lastAnalysis = (state.last_analysis_id ?? null);
            setAnalysisId(lastAnalysis);
            setLatestState(topic
                ? {
                    topic,
                    needs_more_info: false,
                    missing_fields: [],
                    suggested_followups: [],
                }
                : null);
        }
        catch {
            // conversation not found or error — silently ignore
        }
        finally {
            setLoadingConv(false);
        }
    }, []);
    const selectConversation = useCallback((id) => {
        if (id === conversationId)
            return;
        setMobilePanel(null);
        navigate(`/session/${id}`);
    }, [conversationId, navigate]);
    const startNew = useCallback(() => {
        setConversationId(null);
        setMessages([]);
        setAnalysisId(null);
        setLatestState(null);
        setBirthInfo(null);
        setMobilePanel(null);
        navigate("/session");
    }, [navigate]);
    const send = async (textInput) => {
        const text = (textInput ?? input).trim();
        if (!text || loading)
            return;
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
            const res = await sendChatMessage({
                conversation_id: conversationId ?? undefined,
                message: text,
            });
            setConversationId(res.conversation_id);
            navigate(`/session/${res.conversation_id}`, { replace: true });
            setAnalysisId(res.analysis_id);
            setLatestState(res.state);
            setMessages((prev) => prev.map((message) => message.id === pendingId
                ? {
                    ...message,
                    content: res.reply,
                    analysis_id: res.analysis_id,
                    followups: res.state.suggested_followups,
                    pending: false,
                }
                : message));
            refreshConversations();
        }
        catch (err) {
            const message = err instanceof Error ? err.message : "发送失败";
            setMessages((prev) => prev.map((item) => item.id === pendingId
                ? {
                    ...item,
                    content: `这一卦未能成象：${message}`,
                    pending: false,
                    error: true,
                }
                : item));
        }
        finally {
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
        if (!urlConversationId)
            return;
        if (urlConversationId === conversationId)
            return;
        void loadConversation(urlConversationId);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [urlConversationId]);
    const onKeyDown = (event) => {
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
        }
        else {
            const code = window.prompt("输入管理员口令");
            if (code !== ADMIN_CODE)
                return;
            window.localStorage.setItem("bazibase-admin-mode", "1");
        }
        setAdminMode(next);
    };
    const needsMore = latestState?.needs_more_info ?? false;
    const missingLabels = latestState?.missing_fields.map(fieldLabel).join("、") ?? "";
    const railFollowups = latestState?.suggested_followups ?? [];
    const currentTopic = latestState?.topic ?? null;
    const currentConv = conversations.find((c) => c.id === conversationId);
    return (_jsxs("div", { className: "oracle", children: [_jsx("div", { className: "oracle__grain", "aria-hidden": true }), _jsx("div", { className: "oracle__glow", "aria-hidden": true }), _jsxs("header", { className: "oracle-header", children: [_jsxs("div", { className: "oracle-header__brand", children: [_jsx("button", { type: "button", className: "oracle-header__nav oracle-header__nav--left", onClick: () => setMobilePanel(mobilePanel === "archive" ? null : "archive"), "aria-label": "\u6848\u5377", children: "\u6848" }), _jsx("img", { className: "oracle-header__logo", src: logo, alt: "\u58A8\u9274", role: "button", onClick: () => navigate("/") }), _jsx("span", { className: "oracle-header__mark", children: "\u58A8\u9274" }), _jsx("span", { className: "oracle-header__rule", "aria-hidden": true }), _jsx("span", { className: "oracle-header__sub", children: "\u5929\u547D\u53EF\u9274\uFF0C\u6765\u8005\u53EF\u95EE\u3002" }), _jsx("button", { type: "button", className: "oracle-header__nav oracle-header__nav--right", onClick: () => setMobilePanel(mobilePanel === "rail" ? null : "rail"), "aria-label": "\u6848\u5934", children: "\u6CE8" })] }), _jsx("div", { className: "oracle-header__actions", children: _jsx(ThemeSwitcher, {}) })] }), _jsxs("main", { className: `oracle-body ${archiveCollapsed ? "is-archive-collapsed" : ""} ${railCollapsed ? "is-rail-collapsed" : ""}`, children: [_jsxs("aside", { className: `archive ${mobilePanel === "archive" ? "is-open" : ""}`, children: [_jsxs("div", { className: "archive__head", children: [_jsx("span", { className: "archive__label", children: "\u6848\u5377" }), _jsx("span", { className: "archive__tag", children: "ANS" }), _jsx("button", { type: "button", className: "panel-collapse panel-collapse--archive", onClick: () => setArchiveCollapsed(true), "aria-label": "\u6536\u8D77\u6848\u5377", children: "\u3008" })] }), _jsxs("button", { type: "button", className: `archive__new ${!conversationId ? "is-active" : ""}`, onClick: startNew, children: [_jsx("span", { className: "archive__new-mark", children: "\uFF0B" }), _jsx("span", { className: "archive__new-text", children: "\u65B0\u5F00\u4E00\u5C40" })] }), _jsxs("div", { className: "archive__list", children: [conversations.length === 0 && (_jsxs("div", { className: "archive__empty", children: [_jsx("span", { children: "\u5C1A\u65E0\u6848\u5377" }), _jsx("span", { className: "archive__empty-hint", children: "\u9001\u51FA\u7B2C\u4E00\u53E5\u5373\u5F00\u5377" })] })), conversations.map((conv) => (_jsxs("button", { type: "button", className: `slip ${conv.id === conversationId ? "is-active" : ""}`, onClick: () => void selectConversation(conv.id), disabled: loadingConv, children: [_jsx("div", { className: "slip__edge", "aria-hidden": true }), _jsxs("div", { className: "slip__top", children: [_jsx("span", { className: `slip__topic ${conv.topic ? "has-topic" : "no-topic"}`, children: conv.topic ? topicText(conv.topic) : "待定" }), _jsx("span", { className: "slip__time", children: relativeTime(conv.last_message_at) })] }), _jsx("div", { className: "slip__excerpt", children: conv.excerpt || "（未落字）" }), _jsxs("div", { className: "slip__foot", children: [_jsx("span", { className: "slip__gender", children: genderText(conv.gender) }), _jsxs("span", { className: "slip__count", children: [conv.message_count, "\u5219"] })] })] }, conv.id)))] })] }), _jsxs("section", { className: "oracle-chat", children: [messages.length === 0 ? (_jsx("div", { className: "oracle-empty oracle-empty--slim", children: _jsx("p", { className: "oracle-empty__hint", children: "\u65B0\u5C40\u5DF2\u5F00\uFF0C\u843D\u5B57\u95EE\u547D\u3002" }) })) : (_jsxs("div", { className: "message-stream", children: [messages.map((message) => (_jsxs("article", { className: `message message--${message.role} ${message.pending ? "is-pending" : ""} ${message.error ? "is-error" : ""}`, children: [_jsx("div", { className: "message__body", children: message.pending ? (_jsxs("span", { className: "message__loading", children: [_jsx("span", {}), _jsx("span", {}), _jsx("span", {})] })) : (message.content) }), !message.pending && (_jsxs("div", { className: "message__meta", children: [message.role === "assistant" && (_jsx("span", { className: "message__seal", children: "\u58A8" })), message.analysis_id && (_jsx("span", { className: "message__id", children: message.analysis_id }))] })), !message.pending &&
                                                !message.error &&
                                                message.followups &&
                                                message.followups.length > 0 && (_jsx("div", { className: "message__followups", children: message.followups.map((f) => (_jsx("button", { type: "button", className: "followup-chip", onClick: () => void send(f), disabled: loading, children: f }, f))) }))] }, message.id))), _jsx("div", { ref: bottomRef })] })), _jsxs("div", { className: "composer", children: [_jsx("textarea", { className: "composer__input", value: input, onChange: (e) => setInput(e.target.value), onKeyDown: onKeyDown, placeholder: "\u751F\u8FB0\u3001\u5730\u70B9\u3001\u6027\u522B\uFF0C\u4E0E\u4F60\u60F3\u95EE\u7684\u4E8B\u2014\u2014\u4E00\u53E5\u8BDD\u5373\u53EF\u3002", rows: 3 }), _jsxs("div", { className: "composer__bar", children: [_jsxs("span", { className: "composer__hint", children: ["\u56DE\u8F66\u53D1\u9001 ", _jsx("i", { children: "\u00B7" }), " Shift+\u56DE\u8F66\u6362\u884C"] }), _jsx("button", { type: "button", className: "composer__send", onClick: () => void send(), disabled: loading || !input.trim(), children: loading ? "推演中" : "送出" })] })] })] }), _jsxs("aside", { className: `insight-rail ${mobilePanel === "rail" ? "is-open" : ""}`, children: [_jsx("button", { type: "button", className: "panel-collapse panel-collapse--rail", onClick: () => setRailCollapsed(true), "aria-label": "\u6536\u8D77\u6848\u5934", children: "\u3009" }), _jsxs("div", { className: "rail-card", children: [_jsx("div", { className: "rail-card__label", children: "\u5F53\u524D\u6240\u95EE" }), _jsx("div", { className: "rail-card__value", children: currentTopic || currentConv?.topic
                                            ? topicText(currentTopic ?? currentConv?.topic)
                                            : "——" }), needsMore && missingLabels && (_jsxs("div", { className: "rail-card__alert", children: ["\u5C1A\u7F3A ", _jsx("strong", { children: missingLabels }), "\uFF0C\u65B9\u53EF\u6392\u76D8"] })), !needsMore && (currentTopic || currentConv?.topic) && (_jsx("div", { className: "rail-card__meta", children: "\u5DF2\u6392\u76D8 \u00B7 \u53EF\u7EED\u95EE\u7EC6\u8282" }))] }), birthInfo &&
                                (birthInfo.birth_date ||
                                    birthInfo.birth_time ||
                                    birthInfo.birth_place) && (_jsxs("div", { className: "rail-card rail-card--birth", children: [_jsx("div", { className: "rail-card__label", children: "\u751F\u8FB0" }), _jsxs("dl", { className: "birth-grid", children: [birthInfo.birth_date && (_jsxs("div", { className: "birth-row", children: [_jsx("dt", { children: "\u65E5" }), _jsx("dd", { children: birthInfo.birth_date })] })), birthInfo.birth_time && (_jsxs("div", { className: "birth-row", children: [_jsx("dt", { children: "\u65F6" }), _jsx("dd", { children: birthInfo.birth_time })] })), birthInfo.birth_place && (_jsxs("div", { className: "birth-row", children: [_jsx("dt", { children: "\u5730" }), _jsx("dd", { children: birthInfo.birth_place })] })), _jsxs("div", { className: "birth-row", children: [_jsx("dt", { children: "\u9020" }), _jsx("dd", { children: genderText(birthInfo.gender) })] })] })] })), railFollowups.length > 0 && (_jsxs("div", { className: "rail-card", children: [_jsx("div", { className: "rail-card__label", children: "\u53EF\u7EED\u95EE" }), _jsx("div", { className: "rail-chips", children: railFollowups.map((f) => (_jsx("button", { type: "button", className: "rail-chip", onClick: () => void send(f), disabled: loading, children: f }, f))) })] }))] })] }), _jsx("button", { type: "button", className: `edge-tab edge-tab--left ${archiveCollapsed ? "is-visible" : ""}`, onClick: () => setArchiveCollapsed(false), "aria-label": "\u5C55\u5F00\u6848\u5377", children: "\u6848\u3009" }), _jsx("button", { type: "button", className: `edge-tab edge-tab--right ${railCollapsed ? "is-visible" : ""}`, onClick: () => setRailCollapsed(false), "aria-label": "\u5C55\u5F00\u6848\u5934", children: "\u3008\u6CE8" }), mobilePanel && (_jsx("div", { className: "oracle__scrim", onClick: () => setMobilePanel(null), "aria-hidden": true }))] }));
}
