import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { once } from 'node:events';
import { configuration, createGate, passwordHash, safeNext } from './gate.mjs';

const password = 'isolated-test-password-only';
const hash = await passwordHash(password);
const directory = mkdtempSync(join(tmpdir(), 'stand-gate-'));
let count = 0;
function config(extra = {}) {
  return configuration({ STAND_ORIGIN: 'https://preview.example.test', STAND_PASSWORD_HASH: hash,
    STAND_SIGNING_KEY: 'isolated-signing-key-never-used-in-production', STAND_STATE_FILE: join(directory, `${count++}.json`), ...extra });
}
async function fixture(t, options = {}) {
  const cfg = options.config || config();
  const server = createGate(cfg, options.clock);
  server.listen(0, '127.0.0.1'); await once(server, 'listening');
  t.after(() => new Promise(resolve => server.close(resolve)));
  const base = `http://127.0.0.1:${server.address().port}`;
  const request = (path, init = {}) => fetch(base + path, { redirect: 'manual', ...init });
  async function form() {
    const response = await request('/_stand/access?next=%2Fclients');
    const html = await response.text();
    return { csrf: html.match(/name="csrf" value="([^"]+)"/)[1], cookie: response.headers.get('set-cookie').split(';')[0], html, response };
  }
  const post = (f, value = password, extra = {}) => request('/_stand/access', {
    method: 'POST', headers: { origin: cfg.origin, cookie: f.cookie, 'content-type': 'application/x-www-form-urlencoded', 'x-stand-client': '127.0.0.1', ...extra.headers },
    body: new URLSearchParams({ csrf: f.csrf, password: value, next: '/clients', ...extra.body }),
  });
  const verify = (cookie = '', uri = '/api/clients', method = 'GET', headers = {}) => request('/verify', { headers: { cookie, 'x-forwarded-uri': uri, 'x-forwarded-method': method, ...headers } });
  return { request, form, post, verify, cfg, server };
}
test('configuration fails closed, no insecure non-local origin or wildcard webhook', () => {
  assert.throws(() => configuration({}));
  for (const bad of [{ STAND_PASSWORD_HASH: '' }, { STAND_SIGNING_KEY: '' }, { STAND_ORIGIN: 'http://public.test' }, { STAND_STATE_FILE: '' }, { STAND_WEBHOOK_PATHS: '["/api/*"]' }]) assert.throws(() => config(bad));
});
test('all content is denied without a valid session; no fake identity headers', async t => {
  const f = await fixture(t);
  for (const path of ['/', '/api/clients', '/assets/app.js', '/media/private.pdf', '/admin', '/_next/static/test.js']) {
    assert.equal((await f.verify('', path, 'GET', { 'x-stand-authorized': 'true' })).status, 401);
  }
  assert.equal((await f.request('/verify')).status, 403);
  const document = await f.verify('', '/clients', 'GET', { accept: 'text/html' });
  assert.equal(document.status, 303); assert.equal(document.headers.get('location'), '/_stand/access?next=%2Fclients');
});
test('password-only form, wrong-password recovery, valid session and protected cookie', async t => {
  const f = await fixture(t), form = await f.form();
  assert.equal(form.response.status, 200);
  // no-referrer makes Chromium submit Origin:null and breaks same-origin forms.
  assert.equal(form.response.headers.get('referrer-policy'), 'strict-origin-when-cross-origin');
  assert.ok(!form.html.includes('name="username"'));
  assert.match(form.html, /type="password"/);
  const wrong = await f.post(form, 'wrong-test-password');
  assert.equal(wrong.status, 401); assert.match(await wrong.text(), /Неверный пароль/);
  const result = await f.post(form);
  assert.equal(result.status, 303); assert.equal(result.headers.get('location'), '/clients');
  const cookie = result.headers.get('set-cookie');
  assert.match(cookie, /^__Host-stand_crm_access=/); assert.match(cookie, /HttpOnly; SameSite=Lax; Max-Age=28800; Secure/);
  assert.equal((await f.verify(cookie.split(';')[0])).status, 204);
  assert.equal((await f.verify(cookie.split(';')[0] + 'tampered')).status, 401);
  assert.equal(result.headers.get('cache-control'), 'no-store, private');
});
test('CSRF, origin, body type and body size are enforced before password verification', async t => {
  const f = await fixture(t), form = await f.form();
  assert.equal((await f.post(form, password, { headers: { origin: 'https://attacker.test' } })).status, 403);
  assert.equal((await f.post(form, password, { body: { csrf: 'fake' } })).status, 403);
  assert.equal((await f.post(form, password, { headers: { 'content-type': 'application/json' } })).status, 415);
  assert.equal((await f.post(form, 'x'.repeat(5000))).status, 413);
});
test('sessions expire, signing/password rotation revoke access; logout clears cookie', async t => {
  let now = Date.now();
  const f = await fixture(t, { clock: () => now }), form = await f.form();
  const result = await f.post(form), cookie = result.headers.get('set-cookie').split(';')[0];
  const rotated = await fixture(t, { config: { ...f.cfg, hash: await passwordHash('another-isolated-password') } });
  assert.equal((await rotated.verify(cookie)).status, 401);
  const keyRotated = await fixture(t, { config: { ...f.cfg, secret: 'changed-signing-key-for-isolated-test' } });
  assert.equal((await keyRotated.verify(cookie)).status, 401);
  const logout = await f.request('/_stand/logout', { method: 'POST', headers: { origin: f.cfg.origin, cookie: form.cookie + '; ' + cookie, 'content-type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams({ csrf: form.csrf }) });
  assert.match(logout.headers.get('set-cookie'), /Max-Age=0/);
  now += 8 * 3600 * 1000 + 1;
  assert.equal((await f.verify(cookie)).status, 401);
});
test('expired CSRF form is rejected and a fresh form can recover', async t => {
  let now = Date.now();
  const f = await fixture(t, { clock: () => now }), old = await f.form();
  now += 1801 * 1000;
  assert.equal((await f.post(old)).status, 403);
  assert.equal((await f.post(await f.form())).status, 303);
});
test('exact POST-only webhook exemption leaves signature validation to application', async t => {
  const f = await fixture(t, { config: config({ STAND_WEBHOOK_PATHS: '["/api/integrations/ycloud/webhook/"]' }) });
  assert.equal((await f.verify('', '/api/integrations/ycloud/webhook/', 'POST')).status, 204);
  for (const path of ['/api/integrations/ycloud/webhook/', '/api/integrations/ycloud/webhook/x', '/api/integrations/ycloud/webhook/../clients']) assert.equal((await f.verify('', path)).status, 401);
  assert.equal((await f.verify('', '/api/integrations/ycloud/webhook/x', 'POST')).status, 401);
});
test('throttle survives restart and cannot be reset by changing forwarded-for', async t => {
  const f = await fixture(t), form = await f.form();
  for (let i = 0; i < 10; i++) assert.equal((await f.post(form, 'wrong-test-password', { headers: { 'x-forwarded-for': `fake-${i}` } })).status, 401);
  assert.equal((await f.post(form)).status, 429);
  const restarted = await fixture(t, { config: f.cfg });
  assert.equal((await restarted.post(form)).status, 429);
});
test('global guessing cap covers distributed attempts and recovers after its window', async t => {
  let now = Date.now();
  const f = await fixture(t, { clock: () => now }), form = await f.form();
  for (let i = 0; i < 120; i++) assert.equal((await f.post(form, 'short', { headers: { 'x-stand-client': `192.0.2.${i}` } })).status, 401);
  assert.equal((await f.post(form)).status, 429);
  now += 901 * 1000;
  assert.equal((await f.post(form)).status, 303);
});
test('redirects cannot escape origin or inject markup; locales render', async t => {
  for (const path of ['https://evil.test', '//evil.test', '/\\evil.test', '/\nevil', '/_stand/access']) assert.equal(safeNext(path), '/');
  const f = await fixture(t);
  for (const lang of ['ru', 'kk', 'en']) {
    const result = await f.request(`/_stand/access?lang=${lang}&next=${encodeURIComponent('/<script>alert(1)</script>')}`), html = await result.text();
    assert.match(html, new RegExp(`<html lang="${lang}">`)); assert.ok(!html.includes('<script>alert(1)</script>'));
    assert.match(result.headers.get('content-security-policy'), /default-src 'none'/);
  }
});
process.on('exit', () => rmSync(directory, { recursive: true, force: true }));
test('CRM and Market forms and sessions coexist on the same hostname', async t => {
  const crm = await fixture(t), market = await fixture(t, { config: config({ STAND_PRODUCT: 'Market' }) });
  const a = await crm.form(), b = await market.form();
  assert.notEqual(a.cookie.split('=')[0], b.cookie.split('=')[0]);
  const jar = a.cookie + '; ' + b.cookie;
  const first = await crm.post({ ...a, cookie: jar });
  const second = await market.post({ ...b, cookie: jar });
  assert.equal(first.status, 303); assert.equal(second.status, 303);
  const sessions = first.headers.get('set-cookie').split(';')[0] + '; ' + second.headers.get('set-cookie').split(';')[0];
  assert.equal((await crm.verify(sessions)).status, 204);
  assert.equal((await market.verify(sessions)).status, 204);
});
