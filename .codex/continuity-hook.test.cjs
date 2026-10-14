'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const {buildResponse} = require('./continuity-hook.cjs');
test('legacy identities and pending transitions cannot block or instruct a task', () => {
  for (const id of ['primary', 'other', 'retired', undefined]) {
    for (const event of ['SessionStart', 'UserPromptSubmit']) {
      assert.deepEqual(buildResponse({session_id:id,hook_event_name:event,source:'compact'},
        {primaryThreadId:'primary',retiredThreadIds:['retired'],transition:'awaiting_archive'}), {});
    }
  }
});
test('cached command is inert even with malformed input', () => {
  const out = spawnSync(process.execPath,[path.join(__dirname,'continuity-hook.cjs')],
    {input:'PRIVATE_SENTINEL{',encoding:'utf8'});
  assert.equal(out.status,0); assert.equal(out.stderr,''); assert.deepEqual(JSON.parse(out.stdout),{});
});
test('no lifecycle hooks or thread ownership registry remain', () => {
  assert.deepEqual(JSON.parse(fs.readFileSync(path.join(__dirname,'hooks.json'),'utf8')).hooks,{});
  const registry=JSON.parse(fs.readFileSync(path.join(__dirname,'project-session.json'),'utf8'));
  for(const key of ['primaryThreadId','retiredThreadIds','successorThreadId','transition','autoHandoffEnabled','handoff']) {
    assert.equal(Object.hasOwn(registry,key),false);
  }
});
