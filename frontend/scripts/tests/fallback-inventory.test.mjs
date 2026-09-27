import assert from "node:assert/strict";
import test from "node:test";

import { buildFallbackInventory, constantApiArguments, verifyFallbackInventory } from "../check-fallback-inventory.mjs";

test("constant API paths resolve lexically without executing or guessing dynamic values", () => {
  const source = [
    'const path = "/api/client-payments/";',
    'apiClient.get(path);',
    'apiClient.get(`${path}link-options/`);',
    'function shadow(path: string) { apiClient.post(path); }',
    'const dynamic = getEndpoint(); apiClient.get(dynamic);',
    'let mutable = "/api/old/"; mutable = "/api/new/"; apiClient.get(mutable);',
  ].join("\n");
  const values = constantApiArguments(source);
  assert.equal(values.get(source.indexOf("apiClient.get(path)")), "/api/client-payments/");
  assert.equal(values.get(source.indexOf("apiClient.get(`${path}")), "/api/client-payments/link-options/");
  assert.equal(values.has(source.indexOf("apiClient.post(path)")), false);
  assert.equal(values.has(source.indexOf("apiClient.get(dynamic)")), false);
  assert.equal(values.has(source.indexOf("apiClient.get(mutable)")), false);
});

test("fallback registry covers routes, API operations, jobs and provider states", () => {
  const inventory = buildFallbackInventory();
  assert.ok(inventory.routes.length > 0);
  assert.ok(inventory.apiOperations.some((operation) => operation.kind === "query"));
  assert.ok(inventory.apiOperations.some((operation) => operation.kind === "mutation"));
  assert.ok(inventory.backgroundTasks.length > 0);
  assert.ok(inventory.providerStatuses.length > 0);
  assert.deepEqual(inventory.unresolvedApiCalls, []);
  const receipt = inventory.apiOperations.find((operation) => operation.method === "POST" && operation.endpoint === "/api/client-payments/");
  assert.ok(receipt);
  assert.equal(receipt.idempotency, "business_submission_id_and_request_hash");
  assert.equal(receipt.automaticRetryAllowed, false);
  assert.match(receipt.permissionOwner, /payments:view\/create\/manage/);
  assert.ok(inventory.apiOperations.some((operation) => operation.method === "GET" && operation.endpoint === "/api/client-payments/link-options/"));
  assert.ok(inventory.apiOperations.filter((operation) => operation.kind === "mutation").every((operation) => !operation.automaticRetryAllowed));
});

test("generated fallback report is current", () => {
  const result = verifyFallbackInventory();
  assert.ok(result.routes > 0);
  assert.ok(result.errorCodes > 0);
});
