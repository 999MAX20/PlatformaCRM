import assert from "node:assert/strict";
import fs from "node:fs";
import { stripTypeScriptTypes } from "node:module";
import test from "node:test";
import vm from "node:vm";

// Evaluate the actual pure policy and actual shared guard without loading Axios,
// browser storage or import.meta.env into Node. No replacement policy is mocked.
const client = fs.readFileSync(new URL("../../src/api/client.ts", import.meta.url), "utf8");
const guard = client.match(/export function isSafeInternalReturnPath\(value: string\) \{[\s\S]*?\n\}/)?.[0];
assert.ok(guard, "The shared return-path guard must remain available for this behavioral test");
const policy = fs.readFileSync(new URL("../../src/features/auth/authReturnPath.ts", import.meta.url), "utf8")
  .replace(/^import .*;\r?\n/m, "");
const source = stripTypeScriptTypes(`${guard}\n${policy}`).replaceAll("export function", "function");
const { getAuthReturnPathFromState, getPostAuthReturnPath } = vm.runInNewContext(
  `${source}\n({ getAuthReturnPathFromState, getPostAuthReturnPath })`,
);

test("authentication preserves flat and legacy MFA return state including query/hash", () => {
  const from = { pathname: "/invite/token", search: "?source=team", hash: "#accept" };
  assert.equal(getAuthReturnPathFromState({ from }), "/invite/token?source=team#accept");
  assert.equal(getAuthReturnPathFromState({ from: { from } }), "/invite/token?source=team#accept");
  assert.equal(getAuthReturnPathFromState(null), undefined);
  assert.equal(getAuthReturnPathFromState({}), undefined);
});

test("authentication rejects external and cross-workspace return destinations", () => {
  for (const path of ["https://example.invalid", "//example.invalid", "javascript:alert(1)", "/application", "/platform-other"]) {
    assert.equal(getPostAuthReturnPath(false, path), "/app");
    assert.equal(getPostAuthReturnPath(true, path), "/platform");
  }
  assert.equal(getPostAuthReturnPath(false, "/platform/merchants"), "/app");
  assert.equal(getPostAuthReturnPath(true, "/app/tasks"), "/platform");
});

test("authentication retains permitted destinations and falls back without context", () => {
  assert.equal(getPostAuthReturnPath(false, "/app/tasks?task=42#activity"), "/app/tasks?task=42#activity");
  assert.equal(getPostAuthReturnPath(true, "/platform/merchants?search=clinic"), "/platform/merchants?search=clinic");
  assert.equal(getPostAuthReturnPath(false, "/invite/token"), "/invite/token");
  assert.equal(getPostAuthReturnPath(true, "/invite/token"), "/invite/token");
  assert.equal(getPostAuthReturnPath(false), "/app");
  assert.equal(getPostAuthReturnPath(true), "/platform");
});
