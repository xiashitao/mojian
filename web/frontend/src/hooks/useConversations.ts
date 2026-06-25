import { useCallback, useEffect, useState } from "react";
import { listConversations } from "../api/conversationApi";
import type { ConversationSummary } from "../types/api";

/** Loads and refreshes the conversation list for the archive. */
export function useConversations() {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);

  const refresh = useCallback(() => {
    listConversations()
      .then(setConversations)
      .catch(() => {});
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { conversations, refresh } as const;
}
