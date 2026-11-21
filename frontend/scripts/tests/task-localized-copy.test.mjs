import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import test from "node:test";
import ts from "typescript";

function load(file, modules = {}) {
  const exports = {};
  const source = fs.readFileSync(new URL(`../../src/${file}`, import.meta.url), "utf8");
  vm.runInNewContext(ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText,
    { exports, require: name => { if (!(name in modules)) throw new Error(name); return modules[name]; } });
  return exports;
}
const copy = load("lib/taskCopy.ts");
const translate = (key, values) => `${key}:${values?.id ?? ""}`;
const automatic = { id: 1, business: 7, title: "Stored title", description: "Stored description", appointment: 9,
  system_copy: { title: true, description: true, status: "cancelled" } };

test("formatter translates only provenance-backed unchanged copy", () => {
  assert.equal(copy.taskTitle(automatic, translate), "taskWorkspace.followUp.cancelled.title:9");
  assert.equal(copy.taskDescription(automatic, translate), "taskWorkspace.followUp.cancelled.description:");
  assert.equal(copy.taskTitle({ ...automatic, system_copy: null }, translate), automatic.title);
  assert.equal(copy.taskTitle({ ...automatic, system_copy: { ...automatic.system_copy, title: false } }, translate), automatic.title);
});

test("parent task choices send locale and share the title formatter without altering user copy", async () => {
  let request;
  const modules = Object.fromEntries(["appointments", "bots", "clients", "deals", "leads", "resources"].map(name => [`./${name}`, {}]));
  modules["./tasks"] = { tasksApi: { list: async params => { request = params; return [automatic, { id: 2, business: 7, title: "User title" }, { ...automatic, id: 3, business: 8 }]; } } };
  modules["../lib/format"] = {};
  modules["../lib/taskCopy"] = copy;
  const api = load("api/taskRelations.ts", modules);
  const rows = await api.taskRelationOptions("parent_task", 7, "Связаться", undefined, "UTC", "ru-RU", translate);
  assert.equal(request.locale, "ru");
  assert.equal(request.search, "Связаться");
  assert.equal(rows.length, 2);
  assert.equal(rows[0].label, copy.taskTitle(automatic, translate));
  assert.equal(rows[1].label, "User title");
});
