import { apiGet, apiPost } from "./client";

/** 语音识别是否已在服务端配置（决定是否渲染麦克风按钮）。 */
export function fetchAsrEnabled(): Promise<{ enabled: boolean }> {
  return apiGet<{ enabled: boolean }>("/asr/enabled");
}

/** 上传 base64 WAV，返回识别文本。需登录（401 由调用方处理）。 */
export function recognizeVoice(audioB64: string): Promise<{ text: string }> {
  return apiPost<{ text: string }>("/asr/recognize", { audio: audioB64 });
}
