import { apiGet, apiPost, apiDelete } from "./client";
export function listCharts(q) {
    const query = q ? `?q=${encodeURIComponent(q)}` : "";
    return apiGet(`/charts${query}`);
}
export function saveChart(req) {
    return apiPost("/charts", req);
}
export function deleteChart(id) {
    return apiDelete(`/charts/${id}`);
}
