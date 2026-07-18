import type { RefObject } from "react";
import type { MessageFeedback, UiMessage } from "../../types/session";
import { MessageItem } from "./MessageItem";
import { SessionWelcome } from "./SessionWelcome";

export interface MessageListProps {
  messages: UiMessage[];
  loading: boolean;
  bottomRef: RefObject<HTMLDivElement | null>;
  scrollRef: RefObject<HTMLDivElement | null>;
  onScroll: () => void;
  onSendFollowup: (text: string) => void;
  onFeedback: (id: string, feedback: MessageFeedback) => void;
}

/** Scrollable message stream with an empty placeholder. */
export function MessageList({
  messages,
  loading,
  bottomRef,
  scrollRef,
  onScroll,
  onSendFollowup,
  onFeedback,
}: MessageListProps) {
  return (
    <div className="oracle-chat__scroll" ref={scrollRef} onScroll={onScroll}>
      {messages.length === 0 ? (
        <SessionWelcome onPick={onSendFollowup} />
      ) : (
        <div className="message-stream">
          {messages.map((message) => (
            <MessageItem
              key={message.id}
              message={message}
              loading={loading}
              onSendFollowup={onSendFollowup}
              onFeedback={onFeedback}
            />
          ))}
          <div ref={bottomRef} />
        </div>
      )}
    </div>
  );
}
