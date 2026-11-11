import assert from "node:assert/strict";
import test from "node:test";
import { speechFailure } from "../../src/features/voice/speechFailure.ts";

const failure = (code, retryable = true, status = 503) => ({
  isAxiosError: true, message: "PRIVATE_TRANSCRIPT_AND_SECRET", response: {
    status, data: { code, retryable, detail: "PRIVATE_TRANSCRIPT_AND_SECRET" },
  },
});

test("voice errors use fixed messages and never display provider content", () => {
  for (const [code, key, retryable] of [
    ["speech_payment_required", "payment", false], ["speech_timeout", "timeout", true],
    ["provider_unavailable", "unavailable", true], ["provider_rejected", "configuration", false],
    ["not_configured", "configuration", false], ["rate_limited", "rateLimit", true],
    ["invalid_response", "invalidResponse", false], ["no_speech", "noSpeech", false],
  ]) {
    const result = speechFailure(failure(code));
    assert.equal(result.messageKey, `voice.speechError.${key}`);
    assert.equal(result.retryable, retryable);
    assert.equal(JSON.stringify(result).includes("PRIVATE_TRANSCRIPT_AND_SECRET"), false);
  }
  assert.equal(speechFailure(failure("speech_timeout", false)).retryable, false);
  for (const code of ["__proto__", "constructor", "unexpected"])
    assert.equal(speechFailure(failure(code)).messageKey, "voice.unavailable");
});

test("permission denial is not disguised as transcription failure", () => {
  for (const status of [401, 403, 404]) {
    const result = speechFailure(failure("speech_payment_required", true, status));
    assert.equal(result.messageKey, undefined);
    assert.equal(result.retryable, false);
  }
});

test("client timeout, offline, audio validation and retry delay stay distinct", () => {
  assert.equal(speechFailure({ isAxiosError: true, code: "ECONNABORTED" }).messageKey, "voice.speechError.timeout");
  assert.equal(speechFailure({ isAxiosError: true, code: "ERR_NETWORK" }).messageKey, "voice.speechError.network");
  const validation = failure("validation_error", false, 400);
  validation.response.data.errors = { audio: ["audio_empty"] };
  assert.equal(speechFailure(validation).messageKey, "voice.speechError.noSpeech");
  const limited = failure("rate_limited"); limited.response.data.retry_after_seconds = 3;
  assert.equal(speechFailure(limited).error.retryAfterSeconds, 3);
});
