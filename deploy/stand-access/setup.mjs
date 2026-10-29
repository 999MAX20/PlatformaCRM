// Password input is masked; secrets are written only to an ignored local env file.
import { emitKeypressEvents } from 'node:readline';
import { randomBytes } from 'node:crypto';
import { writeFileSync } from 'node:fs';
import { passwordHash } from './gate.mjs';
const origin = process.argv[2];
const url = new URL(origin || '');
if (url.protocol !== 'https:' || url.origin !== origin) throw new Error('Usage: node deploy/stand-access/setup.mjs https://your-domain');
if (!process.stdin.isTTY) throw new Error('Run in an interactive terminal; never pass a password as an argument');
emitKeypressEvents(process.stdin);
process.stdin.setRawMode(true);
process.stdout.write('Stand password (at least 16 characters): ');
let value = '';
process.stdin.on('keypress', async (text, key) => {
  if (key?.ctrl && key.name === 'c') { process.stdin.setRawMode(false); process.exit(1); }
  if (key?.name === 'backspace') { if (value.length) { value = value.slice(0, -1); process.stdout.write('\b \b'); } return; }
  if (key?.name === 'return') {
    process.stdin.setRawMode(false); process.stdin.pause(); process.stdout.write('\n');
    try {
      const hash = await passwordHash(value); value = '';
      writeFileSync('.env.stand.local', `STAND_ORIGIN=${origin}\nWEB_DOMAIN=${url.host}\nSTAND_PASSWORD_HASH=${hash}\nSTAND_SIGNING_KEY=${randomBytes(32).toString('hex')}\nSTAND_WEBHOOK_PATHS=[]\n`, { flag: 'wx', mode: 0o600 });
      process.stdout.write('Saved .env.stand.local. Keep private; an existing file is never overwritten.\n');
    } catch { process.stderr.write('Not saved: password too short or .env.stand.local already exists/unwritable.\n'); process.exitCode = 1; }
    return;
  }
  if (text && !key?.ctrl && !/[\r\n\x00-\x1f]/.test(text) && value.length < 1024) { value += text; process.stdout.write('*'); }
});
