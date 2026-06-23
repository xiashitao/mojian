import { apiPost } from "./client";
export function castAndDiagnose(input) {
    return apiPost("/chart", input);
}
