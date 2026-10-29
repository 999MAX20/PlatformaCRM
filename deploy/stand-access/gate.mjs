import { createServer } from 'node:http';
import { createHmac, randomBytes, scrypt, timingSafeEqual } from 'node:crypto';
import { promisify } from 'node:util';
import { readFileSync, writeFileSync, renameSync } from 'node:fs';
import { pathToFileURL } from 'node:url';
import { renderPage } from './page.mjs';

const derive = promisify(scrypt);
const WINDOW = 15 * 60 * 1000;
export const ACCESS = '/_stand/access';
export function safeNext(value) {
  if (typeof value !== 'string' || !value.startsWith('/') || value.startsWith('//') || /[\\\x00-\x20]/.test(value)) return '/';
  try {
    const url = new URL(value, 'https://stand.invalid');
    if (url.origin !== 'https://stand.invalid' || url.pathname.startsWith('/_stand/')) return '/';
    return url.pathname + url.search;
  } catch { return '/'; }
}
export async function passwordHash(password, salt = randomBytes(16).toString('hex')) {
  if (password.length < 16 || Buffer.byteLength(password) > 1024) throw new Error('Password must contain 16–1024 bytes');
  return `${salt}:${(await derive(password, salt, 32)).toString('hex')}`;
}
export function configuration(env = process.env) {
  const origin = new URL(env.STAND_ORIGIN || '');
  const local = ['localhost', '127.0.0.1', '[::1]'].includes(origin.hostname);
  if ((origin.protocol !== 'https:' && !(local && origin.protocol === 'http:')) || origin.origin !== env.STAND_ORIGIN) throw new Error('STAND_ORIGIN must be an HTTPS origin (HTTP only on loopback)');
  if (!/^[a-f0-9]{32}:[a-f0-9]{64}$/.test(env.STAND_PASSWORD_HASH || '')) throw new Error('STAND_PASSWORD_HASH is required');
  if ((env.STAND_SIGNING_KEY || '').length < 32) throw new Error('STAND_SIGNING_KEY must have at least 32 characters');
  if (!env.STAND_STATE_FILE) throw new Error('STAND_STATE_FILE is required for persistent throttling');
  const exemptions = JSON.parse(env.STAND_WEBHOOK_PATHS || '[]');
  if (!Array.isArray(exemptions) || exemptions.some(p => typeof p !== 'string' || !/^\/api\/[a-zA-Z0-9_/-]+$/.test(p))) throw new Error('Webhook exceptions must be exact API paths');
  return { origin: origin.origin, secure: origin.protocol === 'https:', hash: env.STAND_PASSWORD_HASH, secret: env.STAND_SIGNING_KEY, stateFile: env.STAND_STATE_FILE, exemptions, product: env.STAND_PRODUCT || 'CRM', ttl: 8 * 3600 };
}
export function createGate(config, clock = Date.now) {
  const prefix = config.secure ? '__Host-' : '';
  const sessionName = `${prefix}stand_access`, csrfName = `${prefix}stand_csrf`;
  const key = createHmac('sha256', config.secret).update(config.hash).digest();
  let attempts = {};
  try { attempts = JSON.parse(readFileSync(config.stateFile, 'utf8')); }
  catch (error) { if (error.code !== 'ENOENT') throw new Error('Cannot read throttle state'); }
  if (!attempts || Array.isArray(attempts) || typeof attempts !== 'object' || Object.values(attempts).some(x => !x || !Number.isFinite(x.until) || !Number.isInteger(x.count))) throw new Error('Invalid throttle state');
  const mac = text => createHmac('sha256', key).update(text).digest('hex');
  const equal = (a, b) => typeof a === 'string' && typeof b === 'string' && Buffer.byteLength(a) === Buffer.byteLength(b) && timingSafeEqual(Buffer.from(a), Buffer.from(b));
  function token(kind, seconds) {
    const body = `${kind}.${Math.floor(clock() / 1000) + seconds}.${randomBytes(16).toString('hex')}`;
    return `${body}.${mac(body)}`;
  }
  function valid(value, kind) {
    if (typeof value !== 'string' || value.length > 200) return false;
    const parts = value.split('.');
    const now = Math.floor(clock() / 1000);
    return parts.length === 4 && parts[0] === kind && /^\d+$/.test(parts[1]) && Number(parts[1]) > now && Number(parts[1]) <= now + config.ttl && equal(parts[3], mac(parts.slice(0, 3).join('.')));
  }
  function cookie(name, value, age) {
    return `${name}=${value}; Path=/; HttpOnly; SameSite=Lax; Max-Age=${age}${config.secure ? '; Secure' : ''}`;
  }
  function throttle(ip) {
    const now = clock();
    for (const [id, entry] of Object.entries(attempts)) if (entry.until <= now) delete attempts[id];
    // Only the trusted edge supplies this address. Never use client X-Forwarded-For.
    const id = mac(ip);
    for (const [bucket, limit] of [['global', 120], [id, 10]]) {
      if ((attempts[bucket]?.count || 0) >= limit) return false;
    }
    for (const bucket of ['global', id]) {
      attempts[bucket] ||= { count: 0, until: now + WINDOW };
      attempts[bucket].count++;
    }
    writeFileSync(`${config.stateFile}.tmp`, JSON.stringify(attempts), { mode: 0o600 });
    renameSync(`${config.stateFile}.tmp`, config.stateFile);
    return true;
  }
  return createServer(async (req, res) => {
    res.setHeader('Cache-Control', 'no-store, private');
    res.setHeader('X-Robots-Tag', 'noindex, nofollow, noarchive');
    res.setHeader('X-Content-Type-Options', 'nosniff');
    res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');
    res.setHeader('X-Frame-Options', 'DENY');
    const send = (status, body = '', type = 'text/plain; charset=utf-8') => { res.writeHead(status, { 'Content-Type': type }); res.end(body); };
    const redirect = target => { res.setHeader('Location', target); send(303); };
    try {
      const url = new URL(req.url, config.origin);
      const cookies = Object.fromEntries((req.headers.cookie || '').split(';').map(x => x.trim().split(/=(.*)/s).slice(0, 2)));
      const lang = ['ru', 'kk', 'en'].includes(url.searchParams.get('lang')) ? url.searchParams.get('lang') : (/^(en|kk)/.exec(req.headers['accept-language'] || '')?.[1] || 'ru');
      const page = (status, next, error = '') => {
        const csrf = valid(cookies[csrfName], 'csrf') ? cookies[csrfName] : token('csrf', 1800);
        const nonce = randomBytes(16).toString('base64');
        res.setHeader('Set-Cookie', cookie(csrfName, csrf, 1800));
        res.setHeader('Content-Security-Policy', `default-src 'none'; style-src 'nonce-${nonce}'; script-src 'nonce-${nonce}'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'`);
        send(status, renderPage({ product: config.product, lang, csrf, next: safeNext(next), error, nonce, unlocked: valid(cookies[sessionName], 'session') }), 'text/html; charset=utf-8');
      };
      if (url.pathname === '/verify' && req.method === 'GET') {
        const original = req.headers['x-forwarded-uri'];
        const method = req.headers['x-forwarded-method'];
        if (typeof original !== 'string' || typeof method !== 'string') return send(403);
        // Exact raw path and POST only: no prefix/normalization bypass or exempt GET content.
        if (method === 'POST' && config.exemptions.includes(original.split('?')[0])) return send(204);
        if (valid(cookies[sessionName], 'session')) return send(204);
        if (method === 'GET' && (req.headers.accept || '').includes('text/html')) return redirect(`${ACCESS}?next=${encodeURIComponent(safeNext(original))}`);
        return send(401, JSON.stringify({ code: 'STAND_ACCESS_REQUIRED', accessUrl: ACCESS }), 'application/json');
      }
      if (url.pathname === ACCESS && req.method === 'GET') return page(200, url.searchParams.get('next'));
      if (![ACCESS, '/_stand/logout'].includes(url.pathname)) return send(404);
      if (req.method !== 'POST') return send(405);
      if (req.headers.origin !== config.origin) return send(403);
      if (!(req.headers['content-type'] || '').startsWith('application/x-www-form-urlencoded')) return send(415);
      const chunks = []; let size = 0;
      for await (const chunk of req) {
        size += chunk.length;
        if (size > 4096) return send(413);
        chunks.push(chunk);
      }
      const form = new URLSearchParams(Buffer.concat(chunks).toString('utf8'));
      if (!valid(cookies[csrfName], 'csrf') || !equal(form.get('csrf'), cookies[csrfName])) return page(403, form.get('next'), 'expired');
      if (url.pathname === '/_stand/logout') {
        res.setHeader('Set-Cookie', cookie(sessionName, '', 0));
        return redirect(ACCESS);
      }
      const ip = req.headers['x-stand-client'];
      if (typeof ip !== 'string' || !ip || ip.length > 100) return send(403);
      if (!throttle(ip)) { res.setHeader('Retry-After', '900'); return page(429, form.get('next'), 'limited'); }
      const password = form.get('password') || '';
      if (password.length < 16 || Buffer.byteLength(password) > 1024) return page(401, form.get('next'), 'wrong');
      const [salt, expected] = config.hash.split(':');
      const actual = (await derive(password, salt, 32)).toString('hex');
      if (!equal(actual, expected)) return page(401, form.get('next'), 'wrong');
      res.setHeader('Set-Cookie', cookie(sessionName, token('session', config.ttl), config.ttl));
      return redirect(safeNext(form.get('next')));
    } catch {
      // Never print a password, cookie, request body or environment value.
      if (!res.headersSent) send(503, 'Access service unavailable'); else res.end();
    }
  });
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const server = createGate(configuration());
  server.requestTimeout = 10_000;
  server.headersTimeout = 10_000;
  server.listen(Number(process.env.PORT || 8080), process.env.HOST || '0.0.0.0');
}
