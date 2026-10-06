import assert from "node:assert/strict";
import test from "node:test";

import {
  canOfferActionRecovery,
  canUseActionFallback,
  canShowSupportDetails,
} from "../../src/components/actions/actionFeedbackPolicy.ts";

const appError = (overrides = {}) => ({
  category: "internal",
  code: "internal_error",
  fieldErrors: {},
  messageKey: "actions.errorGeneric",
  retryable: false,
  retryPolicy: "never_blindly",
  source: "runtime",
  ...overrides,
});

test("validation and authorization failures never offer blind recovery", () => {
  assert.equal(canOfferActionRecovery(appError({ category: "validation", retryable: true }), true), false);
  assert.equal(canOfferActionRecovery(appError({ category: "authentication", retryable: true }), true), false);
  assert.equal(canOfferActionRecovery(appError({ category: "permission", retryable: true }), true), false);
  assert.equal(canOfferActionRecovery(appError({ category: "conflict", retryable: false }), true), false);
  assert.equal(canOfferActionRecovery(appError({ category: "temporary", retryable: true }), true), true);
  assert.equal(canOfferActionRecovery(appError({ category: "offline", retryable: true }), true), true);
  assert.equal(canOfferActionRecovery(appError({ category: "temporary", retryable: true }), false), false);
});

test("transport errors never expose a caller fallback as raw action feedback", () => {
  assert.equal(canUseActionFallback(appError({ category: "offline", source: "network" }), true), false);
  assert.equal(canUseActionFallback(appError({ category: "validation", source: "api" }), true), false);
  assert.equal(canUseActionFallback(appError(), true), true);
  assert.equal(canUseActionFallback(appError(), false), false);
});

test("support references are reserved for technical failures with a real request id", () => {
  for (const category of ["internal", "temporary", "provider"]) {
    assert.equal(canShowSupportDetails(appError({ category, requestId: "request-42" })), true);
    assert.equal(canShowSupportDetails(appError({ category })), false);
  }
  for (const category of ["validation", "authentication", "permission", "not_found", "conflict", "rate_limit", "offline"]) {
    assert.equal(canShowSupportDetails(appError({ category, requestId: "request-42" })), false);
  }
});
