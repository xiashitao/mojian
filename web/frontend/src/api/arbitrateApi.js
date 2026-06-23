import { apiPost } from "./client";
export function runArbitration(input) {
    return apiPost("/arbitrate", input);
}
