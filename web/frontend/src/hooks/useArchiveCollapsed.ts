import { useEffect, useState } from "react";

const LAYOUT_KEY = "bazibase-panel-layout";

function loadCollapsed(): boolean {
  try {
    const raw = localStorage.getItem(LAYOUT_KEY);
    if (!raw) return false;
    const parsed = JSON.parse(raw) as { archiveCollapsed?: boolean };
    return parsed.archiveCollapsed === true;
  } catch {
    return false;
  }
}

/** Left-archive collapse flag, persisted to localStorage. */
export function useArchiveCollapsed() {
  const [collapsed, setCollapsed] = useState(loadCollapsed);

  useEffect(() => {
    localStorage.setItem(
      LAYOUT_KEY,
      JSON.stringify({ archiveCollapsed: collapsed }),
    );
  }, [collapsed]);

  return [collapsed, setCollapsed] as const;
}
