import { create } from "zustand";
import { castAndDiagnose } from "../api/chartApi";
export const useChartStore = create((set) => ({
    loading: false,
    error: null,
    chart: null,
    diagnosis: null,
    lastInput: null,
    castChart: async (input) => {
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
        }
        catch (e) {
            const msg = e instanceof Error ? e.message : "排盘失败";
            set({ loading: false, error: msg });
            throw e;
        }
    },
    clear: () => set({ chart: null, diagnosis: null, error: null, lastInput: null }),
}));
