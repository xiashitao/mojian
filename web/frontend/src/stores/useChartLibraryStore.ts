import { create } from "zustand";
import type { SavedChart, SaveChartRequest } from "../types/api";
import { listCharts, saveChart, deleteChart } from "../api/libraryApi";

interface LibraryState {
  charts: SavedChart[];
  loading: boolean;
  error: string | null;
  fetchCharts: (q?: string) => Promise<void>;
  addChart: (req: SaveChartRequest) => Promise<SavedChart>;
  removeChart: (id: string) => Promise<void>;
}

export const useChartLibraryStore = create<LibraryState>((set, get) => ({
  charts: [],
  loading: false,
  error: null,

  fetchCharts: async (q) => {
    set({ loading: true, error: null });
    try {
      const charts = await listCharts(q);
      set({ charts, loading: false });
    } catch (e) {
      const msg = e instanceof Error ? e.message : "加载失败";
      set({ loading: false, error: msg });
    }
  },

  addChart: async (req) => {
    const saved = await saveChart(req);
    set({ charts: [saved, ...get().charts] });
    return saved;
  },

  removeChart: async (id) => {
    await deleteChart(id);
    set({ charts: get().charts.filter((c) => c.id !== id) });
  },
}));
