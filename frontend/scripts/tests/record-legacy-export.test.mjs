import assert from "node:assert/strict";
import fs from "node:fs";
import { stripTypeScriptTypes } from "node:module";
import vm from "node:vm";
import test from "node:test";

function setup(response) {
  const calls = [];
  const source = fs.readFileSync(new URL("../../src/api/importExport.ts", import.meta.url), "utf8")
    .replace(/^import .*;\r?\n/gm, "");
  const context = {
    apiClient: { get: async (...args) => { calls.push(["get", ...args]); return response; } },
    window: { URL: {
      createObjectURL: blob => { calls.push(["url", blob]); return "blob:export"; },
      revokeObjectURL: url => calls.push(["revoke", url]),
    } },
    document: {
      createElement: () => ({ click() { calls.push(["download", this.download]); }, remove() { calls.push(["remove"]); } }),
      body: { appendChild: () => calls.push(["append"]) },
    },
  };
  const api = vm.runInNewContext(stripTypeScriptTypes(source).replace("export const", "const") + "\nimportExportApi", context);
  return { api, calls };
}

test("legacy synchronous CSV export downloads the response and releases its URL", async () => {
  const blob = new Blob(["id,name\n1,Example"]);
  const { api, calls } = setup({ status: 200, data: blob });
  assert.equal(await api.exportEntity({ business: 7, entity: "leads" }), null);
  assert.equal(calls[0][1], "/api/export/leads/");
  assert.equal(calls[0][2].params.business, 7);
  assert.equal(calls[0][2].responseType, "blob");
  assert.equal(calls.find(call => call[0] === "url")[1], blob);
  assert.equal(calls.find(call => call[0] === "download")[1], "leads.csv");
  assert.equal(calls.at(-1)[0], "revoke");
});

test("queued export returns its job without downloading JSON as CSV", async () => {
  const { api, calls } = setup({ status: 202, data: new Blob([JSON.stringify({ id: 42, status: "pending" })]) });
  const result = await api.exportEntity({ business: 7, entity: "deals" });
  assert.equal(result.id, 42);
  assert.equal(result.status, "pending");
  assert.equal(calls.length, 1);
});

test("malformed queued response fails without producing a bogus file", async () => {
  const { api, calls } = setup({ status: 202, data: new Blob(["unavailable"]) });
  await assert.rejects(api.exportEntity({ business: 7, entity: "leads" }));
  assert.equal(calls.length, 1);
});
