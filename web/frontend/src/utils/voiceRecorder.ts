/** 语音输入录音器：getUserMedia 采集 PCM → 降采样 16k 单声道 → WAV。
 *
 * 不用 MediaRecorder：它的输出格式因浏览器而异（Chrome=webm/opus、
 * iOS Safari=mp4/aac），而火山 ASR 只收 wav/mp3/ogg。直接从音频图抓
 * 原始 PCM 再自己编 WAV，一条路径全平台一致。
 * ScriptProcessorNode 虽标记废弃，但所有浏览器（含老 iOS）都支持，
 * 是语音采集的事实标准做法；AudioWorklet 等价但样板代码多得多。
 */

const TARGET_RATE = 16000;
/** 超过时长自动停止（防止忘关麦克风一直录）。 */
export const MAX_RECORD_SECONDS = 60;

export interface VoiceRecorder {
  /** 停止录音并返回 WAV blob；没采到任何声音时返回 null。 */
  stop(): Promise<Blob | null>;
  /** 放弃录音，释放麦克风。 */
  cancel(): void;
}

export async function startRecording(
  onAutoStop?: () => void,
): Promise<VoiceRecorder> {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const AC =
    window.AudioContext ||
    (window as unknown as { webkitAudioContext: typeof AudioContext })
      .webkitAudioContext;
  const ctx = new AC();
  // iOS Safari 的 AudioContext 可能以 suspended 状态创建，需在用户手势内恢复。
  if (ctx.state === "suspended") void ctx.resume();

  const source = ctx.createMediaStreamSource(stream);
  const processor = ctx.createScriptProcessor(4096, 1, 1);
  const chunks: Float32Array[] = [];
  let stopped = false;

  processor.onaudioprocess = (e) => {
    if (!stopped) chunks.push(new Float32Array(e.inputBuffer.getChannelData(0)));
  };
  source.connect(processor);
  // Safari 只有接到 destination 才会驱动 onaudioprocess；
  // processor 输出缓冲一直是静音，不会外放回声。
  processor.connect(ctx.destination);

  const autoStopTimer = window.setTimeout(() => {
    if (!stopped) onAutoStop?.();
  }, MAX_RECORD_SECONDS * 1000);

  const cleanup = () => {
    stopped = true;
    window.clearTimeout(autoStopTimer);
    processor.disconnect();
    source.disconnect();
    stream.getTracks().forEach((t) => t.stop());
    void ctx.close();
  };

  return {
    async stop() {
      const sampleRate = ctx.sampleRate;
      cleanup();
      const total = chunks.reduce((n, c) => n + c.length, 0);
      if (total === 0) return null;
      const merged = new Float32Array(total);
      let offset = 0;
      for (const c of chunks) {
        merged.set(c, offset);
        offset += c.length;
      }
      return encodeWav(downsample(merged, sampleRate, TARGET_RATE), TARGET_RATE);
    },
    cancel: cleanup,
  };
}

/** 均值抽取降采样（48k/44.1k → 16k）。窗口平均自带低通，避免明显混叠。 */
function downsample(
  input: Float32Array,
  fromRate: number,
  toRate: number,
): Float32Array {
  if (fromRate <= toRate) return input;
  const ratio = fromRate / toRate;
  const outLength = Math.floor(input.length / ratio);
  const out = new Float32Array(outLength);
  for (let i = 0; i < outLength; i++) {
    const start = Math.floor(i * ratio);
    const end = Math.min(Math.floor((i + 1) * ratio), input.length);
    let sum = 0;
    for (let j = start; j < end; j++) sum += input[j];
    out[i] = end > start ? sum / (end - start) : 0;
  }
  return out;
}

/** Float32 PCM → 16bit 单声道 WAV。 */
function encodeWav(samples: Float32Array, sampleRate: number): Blob {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);
  const writeString = (offset: number, s: string) => {
    for (let i = 0; i < s.length; i++) view.setUint8(offset + i, s.charCodeAt(i));
  };
  writeString(0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  writeString(8, "WAVE");
  writeString(12, "fmt ");
  view.setUint32(16, 16, true); // fmt chunk size
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, 1, true); // mono
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true); // byte rate
  view.setUint16(32, 2, true); // block align
  view.setUint16(34, 16, true); // bits per sample
  writeString(36, "data");
  view.setUint32(40, samples.length * 2, true);
  let offset = 44;
  for (let i = 0; i < samples.length; i++, offset += 2) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return new Blob([buffer], { type: "audio/wav" });
}

/** Blob → 不带 data: 前缀的 base64 字符串。 */
export function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = reader.result as string;
      resolve(dataUrl.slice(dataUrl.indexOf(",") + 1));
    };
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(blob);
  });
}
