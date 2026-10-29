// Actual Caddy routing, isolated upstream/credentials. No working app or DB touched.
import { createServer } from 'node:http';
import { once } from 'node:events';
import { spawn } from 'node:child_process';
import { mkdtempSync, readFileSync, writeFileSync, mkdirSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import assert from 'node:assert/strict';
import { configuration, createGate, passwordHash } from './gate.mjs';

const binary = process.env.CADDY_BIN;
if (!binary) throw new Error('Set CADDY_BIN to a local Caddy executable');
const directory = mkdtempSync(join(tmpdir(), 'stand-edge-'));
const keep = process.argv.includes('--serve');
const product = process.env.STAND_TEST_PRODUCT || 'CRM';
const password = 'isolated-preview-password';
const app = createServer(async (req, res) => {
  let body = ''; for await (const chunk of req) body += chunk;
  res.setHeader('Content-Type', 'text/plain'); res.end(`private-upstream:${req.url}:${body}`);
});
app.listen(0, '127.0.0.1'); await once(app, 'listening');
const reserve = createServer(); reserve.listen(0, '127.0.0.1'); await once(reserve, 'listening');
const port = reserve.address().port; await new Promise(resolve => reserve.close(resolve));
const origin = `http://127.0.0.1:${port}`;
const gate = createGate(configuration({ STAND_ORIGIN: origin, STAND_PASSWORD_HASH: await passwordHash(password),
  STAND_SIGNING_KEY: 'isolated-preview-signing-key-no-production', STAND_STATE_FILE: join(directory, 'attempts.json'), STAND_PRODUCT: product,
  STAND_WEBHOOK_PATHS: '["/api/integrations/test-webhook"]' }));
gate.listen(0, '127.0.0.1'); await once(gate, 'listening');
mkdirSync(join(directory, 'static')); writeFileSync(join(directory, 'index.html'), 'private-spa'); writeFileSync(join(directory, 'static', 'test.js'), 'private-static');
const appAddress = `127.0.0.1:${app.address().port}`;
const text = readFileSync(new URL('./Caddyfile', import.meta.url), 'utf8')
  .replace(/^\{\r?\n[\s\S]*?\r?\n\}\s*/, '{\n admin off\n auto_https off\n}\n')
  .replaceAll('{$WEB_DOMAIN}', origin).replaceAll('stand-access:8080', `127.0.0.1:${gate.address().port}`)
  .replaceAll('web:8000', appAddress).replaceAll('web:3000', appAddress).replaceAll('api:4000', appAddress)
  .replace('root * /srv', `root * "${directory.replaceAll('\\', '/')}"`)
  .replace('root * /static', `root * "${join(directory, 'static').replaceAll('\\', '/')}"`);
writeFileSync(join(directory, 'Caddyfile'), text);
const caddy = spawn(binary, ['run', '--config', join(directory, 'Caddyfile'), '--adapter', 'caddyfile'], { windowsHide: true, stdio: ['ignore', 'ignore', 'pipe'] });
let errors = ''; caddy.stderr.on('data', data => { errors += data; });
const request = (path, init = {}) => fetch(origin + path, { redirect: 'manual', ...init });
async function cleanup() {
  if (caddy.exitCode === null) { caddy.kill(); await once(caddy, 'exit'); }
  await Promise.all([new Promise(r => gate.close(r)), new Promise(r => app.close(r))]);
  rmSync(directory, { recursive: true, force: true });
}
try {
  let ready = false;
  for (let i = 0; i < 60; i++) {
    if (caddy.exitCode !== null) throw new Error(errors);
    try { ready = (await request('/_stand/access')).status === 200; } catch { /* starting */ }
    if (ready) break;
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  assert.ok(ready, 'Caddy starts');
  for (const path of ['/', '/api/clients', '/static/test.js', '/assets/app.js', '/_next/static/app.js', '/media/file', '/verify']) {
    const denied = await request(path, { headers: { 'x-forwarded-uri': '/api/integrations/test-webhook', 'x-forwarded-method': 'POST', 'x-stand-client': 'fake', 'x-stand-authorized': 'true' } });
    assert.equal(denied.status, 401, path); assert.ok(!(await denied.text()).includes('private-'));
  }
  const csrfResponse = await request('/_stand/access');
  const csrfCookie = csrfResponse.headers.get('set-cookie').split(';')[0];
  const csrf = (await csrfResponse.text()).match(/name="csrf" value="([^"]+)"/)[1];
  const result = await request('/_stand/access', { method: 'POST', headers: { origin, cookie: csrfCookie, 'content-type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams({ csrf, password, next: '/clients' }) });
  assert.equal(result.status, 303);
  const session = result.headers.get('set-cookie').split(';')[0];
  const ok = await request('/api/clients', { method: 'POST', headers: { cookie: session, 'content-type': 'text/plain' }, body: 'body-preserved' });
  assert.equal(await ok.text(), 'private-upstream:/api/clients:body-preserved');
  assert.equal(ok.headers.get('cache-control'), 'no-store, private');
  assert.equal((await request('/static/test.js', { headers: { cookie: session } })).status, 200);
  assert.equal((await request('/api/integrations/test-webhook', { method: 'POST', body: 'signature-body' })).status, 200);
  assert.equal((await request('/api/integrations/test-webhook')).status, 401);
  assert.equal((await request('/api/integrations/test-webhook/extra', { method: 'POST' })).status, 401);
  console.log(`${product}: real Caddy edge checks PASS`);
  if (keep) {
    console.log(`ISOLATED_PREVIEW_URL=${origin}`);
    process.on('SIGINT', async () => { await cleanup(); process.exit(); });
  } else {
    // A failed auth service must never fall through to the application.
    await new Promise(resolve => gate.close(resolve));
    assert.equal((await request('/api/clients', { headers: { cookie: session } })).status, 502);
    console.log('Gate outage: fail-closed PASS');
    await cleanup();
  }
} catch (error) { await cleanup(); throw error; }
