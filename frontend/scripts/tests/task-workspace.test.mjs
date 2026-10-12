import assert from "node:assert/strict";
import test from "node:test";
import { taskDateISO, taskDateInput, taskGroup } from "../../src/features/tasks/workspaceUtils.ts";

test("task form interprets dates in business time rather than browser time", () => {
  assert.equal(taskDateISO("2026-10-13T00:30", "Asia/Almaty"), "2026-10-12T19:30:00.000Z");
  assert.equal(taskDateInput("2026-10-12T19:30:00Z", "Asia/Almaty"), "2026-10-13T00:30");
  assert.equal(taskDateISO("", "Asia/Almaty"), null);
  assert.throws(() => taskDateISO("2026-03-08T02:30", "America/New_York"));
});

test("deadline groups keep waiting and snoozed tasks overdue and separate closed work", () => {
  const now = new Date("2026-10-12T18:30:00Z");
  const waiting = { status: "waiting", due_at: "2026-10-12T17:00:00Z", snoozed_until: "2026-10-14T10:00:00Z" };
  assert.equal(taskGroup(waiting, "Asia/Almaty", now), "overdue");
  assert.equal(taskGroup({ ...waiting, due_at: "2026-10-12T18:45:00Z" }, "Asia/Almaty", now), "today");
  assert.equal(taskGroup({ ...waiting, due_at: "2026-10-12T19:15:00Z" }, "Asia/Almaty", now), "later");
  assert.equal(taskGroup({ ...waiting, due_at: null }, "Asia/Almaty", now), "noDue");
  assert.equal(taskGroup({ ...waiting, status: "done" }, "Asia/Almaty", now), "done");
  assert.equal(taskGroup({ ...waiting, status: "cancelled" }, "Asia/Almaty", now), "cancelled");
});
