import { useChatSession } from "../hooks/useChatSession";
import { ArchiveRail } from "../components/session/ArchiveRail";
import { ArchiveSidebar } from "../components/session/ArchiveSidebar";
import { ChatHeader } from "../components/session/ChatHeader";
import { ChatContextBar } from "../components/session/ChatContextBar";
import { MessageList } from "../components/session/MessageList";
import { Composer } from "../components/session/Composer";
import { AuthModal } from "../components/auth/AuthModal";

export default function SessionPage() {
  const {
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
    closeAuthPrompt,
  } = useChatSession();

  const latestChart =
    [...messages].reverse().find((m) => m.chart)?.chart ?? null;

  return (
    <div className="oracle">
      <div className="oracle__grain" aria-hidden />
      <div className="oracle__glow" aria-hidden />

      <main
        className={`oracle-body oracle-body--two ${archiveCollapsed ? "is-archive-collapsed" : ""}`}
      >
        <ArchiveRail
          onHome={goHome}
          onExpand={() => setArchiveCollapsed(false)}
          onNew={startNew}
        />

        <ArchiveSidebar
          conversations={conversations}
          conversationId={conversationId}
          loadingConv={loadingConv}
          isOpen={mobilePanel === "archive"}
          onHome={goHome}
          onCollapse={() => setArchiveCollapsed(true)}
          onNew={startNew}
          onSelect={selectConversation}
        />

        <section className="oracle-chat">
          <ChatHeader
            onToggleMobilePanel={() =>
              setMobilePanel(mobilePanel === "archive" ? null : "archive")
            }
          />
          <ChatContextBar
            topic={currentTopic ?? currentConv?.topic}
            birthInfo={birthInfo}
            chart={latestChart}
          />
          <MessageList
            messages={messages}
            loading={loading}
            bottomRef={bottomRef}
            onSendFollowup={(text) => void send(text)}
            onFeedback={setMessageFeedback}
          />
          <Composer
            value={input}
            loading={loading}
            tone={tone}
            onToneChange={setTone}
            onChange={setInput}
            onSend={() => void send()}
            onStop={stop}
          />
        </section>
      </main>

      {mobilePanel && (
        <div
          className="oracle__scrim"
          onClick={() => setMobilePanel(null)}
          aria-hidden
        />
      )}

      {authPrompt && (
        <AuthModal
          onClose={closeAuthPrompt}
          prompt="登录后才能开始对话，你的咨询和记忆会保存在账号里。"
        />
      )}
    </div>
  );
}
