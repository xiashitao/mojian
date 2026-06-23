import { apiGet } from "./client";
export function listConversations() {
    return apiGet("/conversations");
}
export function getConversation(id) {
    return apiGet(`/conversations/${id}`);
}
