import { useChatSession } from "../hooks/useChatSession";
import { ArchiveRail } from "../components/session/ArchiveRail";
import { ArchiveSidebar } from "../components/session/ArchiveSidebar";
import { ChatHeader } from "../components/session/ChatHeader";
import { ChatContextBar } from "../components/session/ChatContextBar";
import { MessageList } from "../components/session/MessageList";
import { Composer } from "../components/session/Composer";
import { AuthModal } from "../components/auth/AuthModal";
import { SubjectConfirmDialog } from "../components/session/SubjectConfirmDialog";

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
    subjectConfirm,
    confirmSubject,
    cancelSubjectConfirm,
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
            onHome={goHome}
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

        {mobilePanel && (
          <div
            className="oracle__scrim"
            /*
             * 位置:必须渲染在 main(.oracle-body)内部。.oracle-body 有
             * z-index:2,是一个层叠上下文;抽屉 .archive 的 z-index:50 只在
             * 这个上下文内有效。若遮罩放在 main 外面(z-index:45 对全局),
             * 会整个盖住 main 连同抽屉,抽屉内所有按钮都点不到——点「新对话」
             * 变成关抽屉。放在 main 内部,45 < 50,遮罩正好垫在抽屉之下、
             * 聊天区之上。
             *
             * 事件:用 onPointerDown 关闭,不用 onClick。
             * 原因:点「案」按钮展开抽屉时,遮罩瞬间出现,移动端 ~300ms 的延迟
             * click 事件会落到刚出现的遮罩上,误触发关闭(ghost click),
             * 表现为「点案展开 → 抽屉立刻被关」或「点抽屉内按钮 → 抽屉被关」。
             * PointerDown 在触摸按下瞬间触发,早于 ghost click,且只对真实手指/鼠标
             * 按压生效,能干净避开这个问题。
             */
            onPointerDown={() => setMobilePanel(null)}
            aria-hidden
          />
        )}
      </main>

      {authPrompt && (
        <AuthModal
          onClose={closeAuthPrompt}
          prompt="登录后才能开始对话，你的咨询和记忆会保存在账号里。"
        />
      )}

      {subjectConfirm && (
        <SubjectConfirmDialog
          birthInfo={subjectConfirm.birthInfo}
          onCancel={cancelSubjectConfirm}
          onConfirm={confirmSubject}
        />
      )}
    </div>
  );
}
