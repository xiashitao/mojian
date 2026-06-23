const BASE_URL = "/api";
export class ApiError extends Error {
    status;
    constructor(status, message) {
        super(message);
        this.status = status;
        this.name = "ApiError";
    }
}
export async function apiPost(path, body) {
    const res = await fetch(`${BASE_URL}${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
    if (!res.ok) {
        let detail = res.statusText;
        try {
            const err = await res.json();
            detail = err.detail || detail;
        }
        catch {
            /* ignore */
        }
        throw new ApiError(res.status, detail);
    }
    return res.json();
}
export async function apiGet(path) {
    const res = await fetch(`${BASE_URL}${path}`);
    if (!res.ok) {
        throw new ApiError(res.status, res.statusText);
    }
    return res.json();
}
export async function apiDelete(path) {
    const res = await fetch(`${BASE_URL}${path}`, { method: "DELETE" });
    if (!res.ok) {
        throw new ApiError(res.status, res.statusText);
    }
    return res.json();
}
