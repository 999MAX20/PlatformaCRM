import axios from "axios";
import { normalizeAppError } from "../../api/appError.ts";

const messages: Record<string, { key: string; retryable: boolean }> = {
  speech_payment_required: { key: "payment", retryable: false },
  speech_timeout: { key: "timeout", retryable: true },
  provider_unavailable: { key: "unavailable", retryable: true },
  provider_rejected: { key: "configuration", retryable: false },
  not_configured: { key: "configuration", retryable: false },
  rate_limited: { key: "rateLimit", retryable: true },
  no_speech: { key: "noSpeech", retryable: false },
  invalid_response: { key: "invalidResponse", retryable: false },
  audio_empty: { key: "noSpeech", retryable: false },
  audio_format: { key: "invalidAudio", retryable: false },
  audio_size: { key: "invalidAudio", retryable: false },
};

export function speechFailure(cause: unknown) {
  const error = normalizeAppError(cause);
  if (["authentication", "permission", "not_found"].includes(error.category)) {
    return { error, messageKey: undefined, retryable: false };
  }
  if (axios.isAxiosError(cause) && !cause.response) {
    const timeout = ["ECONNABORTED", "ETIMEDOUT"].includes(cause.code || "");
    return { error, messageKey: `voice.speechError.${timeout ? "timeout" : "network"}`, retryable: true };
  }
  const data = axios.isAxiosError(cause) ? cause.response?.data : undefined;
  const code = typeof data?.code === "string" ? data.code : "";
  const audioCode = data?.errors?.audio?.[0] ?? data?.audio?.[0];
  const policy = Object.prototype.hasOwnProperty.call(messages, code) ? messages[code]
    : typeof audioCode === "string" && Object.prototype.hasOwnProperty.call(messages, audioCode) ? messages[audioCode] : undefined;
  return {
    error,
    messageKey: policy ? `voice.speechError.${policy.key}` : "voice.unavailable",
    retryable: Boolean(policy?.retryable && data?.retryable !== false),
  };
}
