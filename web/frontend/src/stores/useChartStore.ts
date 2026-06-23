import { create } from "zustand";
import type { Chart } from "../types/chart";
import type { Diagnosis } from "../types/diagnosis";
import type { BirthInput, ChartResponse } from "../types/api";
import { castAndDiagnose } from "../api/chartApi";

interface ChartState {
  loading: boolean;
  error: string | null;
  chart: Chart | null;
  diagnosis: Diagnosis | null;
  lastInput: BirthInput | null;
  castChart: (input: BirthInput) => Promise<ChartResponse>;
  clear: () => void;
}

export const useChartStore = create<ChartState>((set) => ({
  loading: false,
  error: null,
  chart: null,
  diagnosis: null,
  lastInput: null,

  castChart: async (input: BirthInput) => {
    set({ loading: true, error: null });
    try {
      const res = await castAndDiagnose(input);
      set({
        chart: res.chart,
        diagnosis: res.diagnosis,
        lastInput: input,
        loading: false,
      });
      return res;
    } catch (e) {
      const msg = e instanceof Error ? e.message : "排盘失败";
      set({ loading: false, error: msg });
      throw e;
    }
  },

  clear: () =>
    set({ chart: null, diagnosis: null, error: null, lastInput: null }),
}));
