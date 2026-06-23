import { apiGet, apiPost } from "./client";
export function sendChatMessage(req) {
    return apiPost("/chat", req);
}
export function getChatAnalysis(analysisId) {
    return apiGet(`/admin/analyses/${analysisId}`);
}
