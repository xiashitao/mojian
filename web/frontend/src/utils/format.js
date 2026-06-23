const STEM_ELEMENTS = {
    甲: "木", 乙: "木",
    丙: "火", 丁: "火",
    戊: "土", 己: "土",
    庚: "金", 辛: "金",
    壬: "水", 癸: "水",
};
const BRANCH_ELEMENTS = {
    子: "水", 丑: "土",
    寅: "木", 卯: "木",
    辰: "土", 巳: "火",
    午: "火", 未: "土",
    申: "金", 酉: "金",
    戌: "土", 亥: "水",
};
export function getCharElement(char) {
    if (STEM_ELEMENTS[char])
        return STEM_ELEMENTS[char];
    if (BRANCH_ELEMENTS[char])
        return BRANCH_ELEMENTS[char];
    return undefined;
}
/** Returns CSS class for text color, e.g. "el-wood" */
export function elClass(char) {
    const el = getCharElement(char);
    if (!el)
        return "";
    return `el-${el}`;
}
/** Returns CSS class for background tint, e.g. "bg-wood" */
export function bgClass(char) {
    const el = getCharElement(char);
    if (!el)
        return "";
    return `bg-${el}`;
}
const ELEMENT_HEX = {
    木: "#4ade80",
    火: "#f87171",
    土: "#facc15",
    金: "#cbd5e1",
    水: "#60a5fa",
};
export function getElementHex(name) {
    return ELEMENT_HEX[name] || "#94a3b8";
}
