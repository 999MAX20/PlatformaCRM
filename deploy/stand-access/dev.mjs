// Local entry in front of already running canonical dev servers. No DB changes.
import { createGate, configuration } from './gate.mjs';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { parseEnv } from 'node:util';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { resolve } from 'node:path';

const product = process.argv[2];
if (!['CRM', 'Market'].includes(product)) throw new Error('Usage: node deploy/stand-access/dev.mjs CRM|Market');
const env = parseEnv(readFileSync(resolve('.env.stand.local'), 'utf8'));
const origin = new URL(env.STAND_ORIGIN);
if (origin.protocol !== 'http:' || !['127.0.0.1', 'localhost', '[::1]'].includes(origin.hostname)) throw new Error('Local gate requires an HTTP loopback origin');
const upstream = product === 'CRM' ? '127.0.0.1:5173' : '127.0.0.1:3000';
const directory = resolve('output/stand-access-live');
mkdirSync(directory, { recursive: true });
const gate = createGate(configuration({ ...env, STAND_PRODUCT: product, STAND_STATE_FILE: resolve(directory, 'attempts.json') }));
gate.listen(0, '127.0.0.1'); await once(gate, 'listening');
const gateAddress = `127.0.0.1:${gate.address().port}`;
const caddyConfig = `{
 admin off
 auto_https off
}
${origin.origin} {
 header {
  Cache-Control "no-store, private"
  X-Robots-Tag "noindex, nofollow, noarchive"
  Referrer-Policy strict-origin-when-cross-origin
 }
 route {
  @gate path /_stand/access /_stand/logout
  handle @gate {
   reverse_proxy ${gateAddress} {
    header_up X-Stand-Client {remote_host}
   }
  }
  forward_auth ${gateAddress} {
   uri /verify
  }
  reverse_proxy ${upstream}
 }
}
`;
const path = resolve(directory, 'Caddyfile.local');
writeFileSync(path, caddyConfig);
const child = spawn(process.env.CADDY_BIN || env.CADDY_BIN || 'caddy', ['run', '--config', path, '--adapter', 'caddyfile'], { windowsHide: true, stdio: ['ignore', 'inherit', 'inherit'] });
child.on('error', () => { console.error('Caddy failed to start; set CADDY_BIN to its executable'); gate.close(); process.exitCode = 1; });
child.on('exit', code => { gate.close(); process.exitCode = code || 0; });
process.on('SIGINT', () => { child.kill(); gate.close(); });
writeFileSync(resolve(directory, 'runtime.json'), JSON.stringify({ product, root: process.cwd(), pid: process.pid, caddyPid: child.pid, origin: origin.origin, upstream: `http://${upstream}` }, null, 2));
console.log(`${product} local gate: ${origin.origin}`);
