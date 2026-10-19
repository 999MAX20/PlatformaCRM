import assert from "node:assert/strict";
import test from "node:test";
import { ruleEditorDraft, conditionText, editedConditionValue, localDateTimeValue, actionUserConfig } from "../../src/features/automations/editorDraft.ts";

test("loading an existing rule preserves condition types and action config without sharing objects", () => {
  const values = [{ value: ["new", "qualified"] }, { value: 123 }, { value: "123" }, true, [1, 2], null];
  const rule = { name: "Saved", trigger_type: "lead_created", description: "Keep", is_active: true, priority: 7,
    conditions: values.map(value => ({ field: "status", operator: "eq", value })),
    actions: [{ action_type: "create_task", delay_seconds: 15, config: { user_id: 9, due_at: "2027-01-01T12:00:00+05:00", title: "Keep" } }] };
  const draft = ruleEditorDraft(rule);
  assert.deepEqual(draft.conditions.map(item => item.value), values);
  assert.deepEqual(draft.actions, rule.actions);
  assert.equal(draft.form.is_active, true);
  assert.equal(draft.form.priority, 7);
  draft.actions[0].config.title = "Changed";
  draft.conditions[0].value.value.push("later");
  assert.equal(rule.actions[0].config.title, "Keep");
  assert.deepEqual(rule.conditions[0].value.value, ["new", "qualified"]);
});

test("condition edits accept typed JSON and ordinary text", () => {
  assert.equal(conditionText({ value: ["a", "b"] }), '["a","b"]');
  assert.deepEqual(editedConditionValue('["a","b"]'), { value: ["a", "b"] });
  assert.deepEqual(editedConditionValue('false'), { value: false });
  assert.deepEqual(editedConditionValue('new'), { value: "new" });
});

test("changing an assignee replaces legacy aliases without conflicts or losing other settings", () => {
  const config = { user_id: 1, owner_id: 1, title: "Keep" };
  assert.deepEqual(actionUserConfig(config, "assignee_id", 2), { title: "Keep", assignee_id: 2 });
  assert.deepEqual(actionUserConfig(config, "assignee_id", ""), { title: "Keep" });
  assert.equal(config.user_id, 1);
});

test("persisted zoned deadlines display as browser local time without changing the source instant", () => {
  const value = "2027-01-01T12:00:00+05:00";
  assert.equal(new Date(localDateTimeValue(value)).getTime(), new Date(value).getTime());
  assert.equal(localDateTimeValue(""), "");
  assert.equal(localDateTimeValue("invalid"), "");
});
