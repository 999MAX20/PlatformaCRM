import assert from "node:assert/strict";
import fs from "node:fs";
import { stripTypeScriptTypes } from "node:module";
import vm from "node:vm";
import test from "node:test";

const source = fs.readFileSync(new URL("../../src/features/calendar/recordFilters.ts", import.meta.url), "utf8");
const { recordWorkspaceParams, nextRecordDay, patchRecordFilters, resetRecordFilters, savedRecordPeriod, recordReturnPath } = vm.runInNewContext(
  stripTypeScriptTypes(source).replaceAll("export ", "") + "\n({ recordWorkspaceParams, nextRecordDay, patchRecordFilters, resetRecordFilters, savedRecordPeriod, recordReturnPath })", { URLSearchParams });

test("ordinary list uses a business day with an exclusive end", () => {
  const query = recordWorkspaceParams(new URLSearchParams(), "2026-12-31", 7);
  assert.equal(query.start_from, "2026-12-31");
  assert.equal(query.start_to, "2027-01-01");
  assert.equal(query.business, 7);
});

test("pending outcomes and client drilldown retain their scope across all dates", () => {
  const query = recordWorkspaceParams(new URLSearchParams("attention=pending_result&client=42&page=2"), "2026-11-02", 7);
  assert.equal(query.attention, "pending_result");
  assert.equal(query.client, "42");
  assert.equal(query.start_from, undefined);
  assert.equal(query.start_to, undefined);
  assert.equal(query.page, "2");
  const explicit = recordWorkspaceParams(new URLSearchParams("attention=pending_result&from=2026-10-01&to=2026-10-31"), "2026-11-02", 7);
  assert.equal(explicit.start_to, "2026-11-01");
});

test("invalid dates reach API validation without silent normalization", () => {
  assert.equal(nextRecordDay("2026-02-30"), "2026-02-30");
  assert.equal(nextRecordDay("not-a-date"), "not-a-date");
  assert.equal(nextRecordDay("2028-02-29"), "2028-03-01");
});


test("atomic draft patch preserves context and resets pagination", () => {
  const current = new URLSearchParams("client=42&from=2026-10-01&to=2026-10-02&page=3&page_size=50&create=1");
  const next = patchRecordFilters(current, { from: "2026-12-01", to: "2026-12-31", confirmed: "false" });
  assert.equal(next.get("client"), "42");
  assert.equal(next.get("page"), null);
  assert.equal(next.get("page_size"), "50");
  assert.equal(next.get("create"), "1");
  assert.equal(current.get("from"), "2026-10-01");
  assert.equal(recordWorkspaceParams(next, "2026-11-03", 7).start_to, "2027-01-01");
  assert.equal(next.get("confirmed"), "false");
});

test("reset removes all filter conditions while preserving unrelated action context", () => {
  const next = resetRecordFilters(new URLSearchParams("client=42&attention=pending_result&resource=2&branch=3&responsible_user=4&confirmed=false&workflow=completed&search=x&from=2026-01-01&to=2026-02-01&ordering=-start_at&page=4&page_size=50&create=1&conversation=8"));
  assert.equal(next.toString(), "page_size=50&create=1&conversation=8");
  assert.equal(recordWorkspaceParams(next, "2026-11-03", 7).start_from, "2026-11-03");
});


test("remembered period excludes client and other context and rejects invalid ranges", () => {
  assert.equal(savedRecordPeriod("from=2026-11-04&to=2026-11-05&client=42&workflow=completed").toString(), "from=2026-11-04&to=2026-11-05");
  assert.equal(savedRecordPeriod("from=2026-11-04").get("to"), "2026-11-04");
  assert.equal(savedRecordPeriod("from=2026-11-05&to=2026-11-04"), null);
  assert.equal(savedRecordPeriod("from=2026-02-30"), null);
  assert.equal(savedRecordPeriod(null), null);
});


test("explicit reset replaces a remembered day with today", () => {
  const reset = resetRecordFilters(new URLSearchParams("from=2026-12-15&workflow=completed"), "2026-11-03");
  assert.equal(reset.toString(), "from=2026-11-03&to=2026-11-03");
});

test("card return preserves list context and rejects external or unrelated destinations", () => {
  const list = "/app/appointments?search=Audit&page=2&workflow=planned&from=2026-12-15";
  assert.equal(recordReturnPath(list), list);
  const plan = "/app/appointments?view=plans&plan=7";
  assert.equal(recordReturnPath(plan), plan);
  for (const value of [null, 3, "https://evil.test", "//evil.test", "/app/appointments/7", "/app/clients", "/app/appointments?x=\n"]) {
    assert.equal(recordReturnPath(value), "/app/appointments");
  }
});
