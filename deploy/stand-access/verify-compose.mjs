import { execFileSync } from 'node:child_process';
import { mkdtempSync, writeFileSync, rmSync, existsSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';
const root = fileURLToPath(new URL('../../', import.meta.url));
const market = existsSync(join(root, 'compose.production.yaml'));
const base = market ? 'compose.production.yaml' : 'docker-compose.yml';
const dir = mkdtempSync(join(tmpdir(), 'stand-compose-'));
const env = join(dir, 'fixture.env');
// Compose versions may stat service env_file even with --no-env-resolution.
// Clear ONLY env_file in a disposable test overlay; never read/create working env.
const blocks = readFileSync(join(root, base), 'utf8').split(/(?=^  [a-z][a-z0-9-]*:\s*$)/m);
const envServices = blocks.filter(block => /^  [a-z][a-z0-9-]*:\s*\n/.test(block) && /^    env_file:/m.test(block))
  .map(block => block.match(/^  ([a-z][a-z0-9-]*):/)[1]);
const fixture = join(dir, 'without-working-env.yaml');
writeFileSync(fixture, 'services:\n' + envServices.map(name => `  ${name}:\n    env_file: !reset []\n`).join(''));
writeFileSync(env, `STAND_ORIGIN=https://preview.example.test\nWEB_DOMAIN=preview.example.test\nSTAND_PASSWORD_HASH=${'a'.repeat(32)}:${'b'.repeat(64)}\nSTAND_SIGNING_KEY=${'test'.repeat(16)}\nREGISTRY=example.invalid/test\nAPP_RELEASE=isolated\n`);
const binary = process.env.COMPOSE_BIN || 'docker';
const prefix = process.env.COMPOSE_BIN ? [] : ['compose'];
try {
  const args = [...prefix, '--env-file', env, '-f', base, '-f', 'compose.stand.yaml', '-f', fixture, 'config', '--no-env-resolution', '--format', 'json'];
  const result = JSON.parse(execFileSync(binary, args, { cwd: root, encoding: 'utf8', windowsHide: true }));
  for (const [name, service] of Object.entries(result.services)) {
    if (name !== 'caddy') assert.ok(!service.ports?.length, `${name} must not publish a bypass port`);
  }
  assert.ok(result.services.caddy.volumes.some(v => v.target === '/etc/caddy/Caddyfile' && v.source.replaceAll('\\', '/').endsWith('/deploy/stand-access/Caddyfile')));
  assert.equal(result.services['stand-access'].environment.STAND_STATE_FILE, '/state/attempts.json');
  assert.equal(result.services['stand-access'].environment.STAND_PRODUCT, market ? 'Market' : 'CRM');
  assert.ok(result.services['stand-access'].volumes.some(v => v.target === '/state'));
  console.log('Compose merge PASS: only Caddy publishes ports; protected routes and persistent state selected');
} finally { rmSync(dir, { recursive: true, force: true }); }
