import { create } from "zustand";
import type { ArbitrationResult } from "../types/api";
import type { BirthInput } from "../types/api";
import { runArbitration } from "../api/arbitrateApi";

interface ArbitrationState {
  loading: boolean;
  error: string | null;
  result: ArbitrationResult | null;
  runArbitration: (input: BirthInput & { threshold?: number }) => Promise<void>;
  clear: () => void;
}

export const useArbitrationStore = create<ArbitrationState>((set) => ({
  loading: false,
  error: null,
  result: null,

  runArbitration: async (input) => {
    set({ loading: true, error: null });
    try {
      const res = await runArbitration(input);
      set({ result: res.arbitration, loading: false });
    } catch (e) {
      const msg = e instanceof Error ? e.message : "仲裁失败";
      set({ loading: false, error: msg });
    }
  },

  clear: () => set({ result: null, error: null }),
}));
