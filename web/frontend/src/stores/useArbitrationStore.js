import { create } from "zustand";
import { runArbitration } from "../api/arbitrateApi";
export const useArbitrationStore = create((set) => ({
    loading: false,
    error: null,
    result: null,
    runArbitration: async (input) => {
        set({ loading: true, error: null });
        try {
            const res = await runArbitration(input);
            set({ result: res.arbitration, loading: false });
        }
        catch (e) {
            const msg = e instanceof Error ? e.message : "仲裁失败";
            set({ loading: false, error: msg });
        }
    },
    clear: () => set({ result: null, error: null }),
}));
