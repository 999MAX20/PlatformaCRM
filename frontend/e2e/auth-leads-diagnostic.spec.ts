import { test, expect, type APIResponse, type Page, type Response } from '@playwright/test';

const api = 'http://127.0.0.1:8000';
const frontend = 'http://127.0.0.1:4173';
const password = process.env.E2E_PASSWORD;
const email = process.env.E2E_OWNER_EMAIL;
if (!password || !email) throw new Error('Disposable synthetic credentials required');
const allowedOrigins = new Set([api, frontend]);
type Observation = {
  events: Array<Record<string, unknown>>; unexpectedOrigins: string[];
  telemetryErrors: string[]; pending: Promise<void>[];
};
const observations = new WeakMap<Page, Observation>();
function obs(page: Page) { const value = observations.get(page); if (!value) throw new Error('Missing diagnostic context'); return value; }
function record(page: Page, event: Record<string, unknown>) {
  const state = obs(page);
  if (state.events.length >= 600) { if (!state.telemetryErrors.includes('event-limit')) state.telemetryErrors.push('event-limit'); return event; }
  const entry = { sequence: state.events.length, observedAtMs: Date.now(), ...event };
  state.events.push(entry); return entry;
}
function safePath(value: string) { return new URL(value).pathname; }
function watch(page: Page, work: Promise<void>) {
  obs(page).pending.push(work.catch(() => { obs(page).telemetryErrors.push('observation-unavailable'); }));
}
async function summarize(page: Page, response: Response | APIResponse, source: string) {
  const url = new URL(response.url());
  const entry: Record<string, unknown> = record(page, { event: 'response', source, origin: url.origin, path: url.pathname, status: response.status() });
  const headers = 'headersArray' in response ? await response.headersArray() : [];
  entry.setCookieFlags = headers.filter(h => h.name.toLowerCase() === 'set-cookie').map(h => ({
    refresh: h.value.startsWith('zani_refresh_token='), httpOnly: /;\s*httponly/i.test(h.value),
    secure: /;\s*secure/i.test(h.value), sameSite: /;\s*samesite=(\w+)/i.exec(h.value)?.[1] ?? null,
    path: /;\s*path=([^;]*)/i.exec(h.value)?.[1] ?? null,
  }));
  if (url.pathname.startsWith('/api/')) {
    const data: unknown = await response.json().catch(() => null);
    if (data && typeof data === 'object') {
      const object = data as Record<string, unknown>;
      if (!response.ok()) {
        entry.errorClass = object.code === 'token_not_valid' ? 'token_not_valid' :
          Object.prototype.hasOwnProperty.call(object, 'refresh') ? 'refresh-field-validation' :
          typeof object.detail === 'string' && /blacklist/i.test(object.detail) ? 'blacklisted-token' :
          Object.prototype.hasOwnProperty.call(object, 'detail') ? 'detail-present' : 'other-json-error';
      }
      if (/^\/api\/(leads|businesses)\/$/.test(url.pathname)) {
        const list = Array.isArray(data) ? data : Array.isArray(object.results) ? object.results : [];
        entry.count = typeof object.count === 'number' ? object.count : list.length;
        entry.ids = list.slice(0, 100).map(row => (row as { id?: unknown }).id).filter(id => typeof id === 'number');
        entry.businessIds = list.slice(0, 100).map(row => (row as { business?: unknown }).business).filter(id => typeof id === 'number');
      }
      if (url.pathname === '/api/auth/me/') {
        entry.merchant = object.is_merchant_user === true;
        entry.businessIds = Array.isArray(object.businesses) ? object.businesses.map(row => (row as { id?: unknown }).id) : [];
      }
    }
  }
}
async function cookies(page: Page, checkpoint: string) {
  const values = await page.context().cookies(`${api}/api/auth/token/refresh/`);
  record(page, { event: 'cookie-shape', checkpoint, cookies: values.map(c => ({
    refresh: c.name === 'zani_refresh_token', domain: c.domain, path: c.path,
    httpOnly: c.httpOnly, secure: c.secure, sameSite: c.sameSite, present: Boolean(c.value),
  })) });
  return values.find(c => c.name === 'zani_refresh_token');
}
test.beforeEach(async ({ page, context }) => {
  observations.set(page, { events: [], unexpectedOrigins: [], telemetryErrors: [], pending: [] });
  await context.route('**/*', async route => {
    const url = new URL(route.request().url());
    if (['http:', 'https:'].includes(url.protocol) && !allowedOrigins.has(url.origin)) {
      obs(page).unexpectedOrigins.push(url.origin); await route.abort('blockedbyclient'); return;
    }
    await route.continue();
  });
  page.on('request', request => {
    const url = new URL(request.url());
    const entry: Record<string, unknown> = record(page, { event: 'request', method: request.method(), origin: url.origin, path: url.pathname,
      authorizationPresent: null, refreshCookiePresent: null });
    watch(page, request.allHeaders().then(headers => {
      entry.authorizationPresent = Boolean(headers.authorization);
      entry.refreshCookiePresent = /(?:^|;\s*)zani_refresh_token=/.test(headers.cookie ?? '');
    }));
  });
  page.on('response', response => { watch(page, summarize(page, response, 'browser')); });
  page.on('pageerror', error => { record(page, { event: 'page-error', name: error.name }); });
  page.on('console', message => { if (message.type() === 'error') record(page, { event: 'console-error', origin: message.location().url ? new URL(message.location().url).origin : null }); });
});
test.afterEach(async ({ page }, info) => {
  const state = obs(page);
  const deadline = Date.now()+4000;
  async function bounded<T>(work: Promise<T>): Promise<T | null> {
    let timer: ReturnType<typeof setTimeout> | undefined;
    try {
      return await Promise.race([work, new Promise<null>(resolve => { timer=setTimeout(() => resolve(null),Math.max(1,deadline-Date.now())); })]);
    } finally { if (timer) clearTimeout(timer); }
  }
  if (await bounded(Promise.all(state.pending)) === null) state.telemetryErrors.push('observation-deadline');
  const dom = await bounded(page.evaluate(() => ({
    path: location.pathname, viewport: { width: innerWidth, height: innerHeight },
    tableRows: [...document.querySelectorAll('div[role="button"][tabindex="0"]')].map(el => ({
      visible: el.getClientRects().length > 0, display: getComputedStyle(el).display,
      childCount: el.children.length, textLength: el.textContent?.length ?? 0,
    })),
    inputTypes: [...document.querySelectorAll('input')].map(el => el.type),
    headings: [...document.querySelectorAll('h1,h2')].map(el => ({ tag: el.tagName, textLength: el.textContent?.length ?? 0 })),
  })).catch(() => null));
  if (dom === null) state.telemetryErrors.push('dom-observation-unavailable');
  const body = JSON.stringify({ name: info.title, events: state.events, unexpectedOrigins: state.unexpectedOrigins,
    telemetryErrors: state.telemetryErrors, dom }, null, 2);
  await info.attach('sanitized-diagnostic', { body: Buffer.from(body), contentType: 'application/json' });
  expect(state.unexpectedOrigins, 'Unexpected external request was blocked').toEqual([]);
  expect(state.telemetryErrors, 'Required observation unavailable').toEqual([]);
});
async function apiLogin(page: Page) {
  record(page, { event: 'request', source: 'test-api-login', method: 'POST', origin: api, path: '/api/auth/token/' });
  const response = await page.request.post(`${api}/api/auth/token/`, { data: { email, password } });
  await summarize(page, response, 'test-api-login');
  expect(response.ok(), 'Synthetic API login').toBeTruthy();
  const payload = await response.json() as { access?: unknown; refresh?: unknown };
  expect(typeof payload.access).toBe('string'); expect(payload.refresh).toBeUndefined();
  const cookie = await cookies(page, 'after-api-login');
  expect(Boolean(cookie?.httpOnly), 'HttpOnly refresh cookie required').toBeTruthy();
  return payload.access as string;
}
// Exact existing smoke helper order: goto root, clear storage, API login, hard goto target.
async function existingHelper(page: Page) {
  await page.goto('/');
  await page.evaluate(() => { localStorage.clear(); sessionStorage.clear(); });
  await apiLogin(page);
  await page.goto('/app');
  await expect(page).toHaveURL(/\/app/);
}
async function uiLogin(page: Page) {
  await page.goto('/login');
  await page.locator('input[type="email"]').fill(email!);
  await page.locator('input[type="password"]').fill(password!);
  await page.locator('form button[type="submit"]').click();
  await expect(page).toHaveURL(/\/app\/?$/);
  await cookies(page, 'after-ui-login');
}
async function ownerRead(page: Page, path: string, access: string) {
  record(page, { event: 'request', source: 'owner-api', method: 'GET', origin: api, path, authorizationPresent: true });
  const response = await page.request.get(api + path, { headers: { Authorization: `Bearer ${access}` } });
  await summarize(page, response, 'owner-api');
  expect(response.ok(), 'Owner API read '+path).toBeTruthy();
  return await response.json() as Record<string, unknown>;
}
async function hardReloadRoutes(page: Page) {
  for (const path of ['/app/clients', '/app/leads']) {
    record(page, { event: 'hard-navigation', path });
    await cookies(page, 'before-'+path);
    for (const reload of [false, true]) {
      const me = page.waitForResponse(r => r.url() === api+'/api/auth/me/', { timeout: 10000 }).catch(() => null);
      if (reload) await page.reload(); else await page.goto(path);
      const response = await me;
      expect(response?.status(), 'Hard navigation must restore actual authenticated user').toBe(200);
      await expect(page.locator('a[href="/app/leads"]:visible').first()).toBeVisible();
      await expect(page).toHaveURL(new RegExp(path+'/?$'));
    }
  }
}
test('API cookie baseline: rotate refresh, me and seeded leads', async ({ page }) => {
  const access = await apiLogin(page);
  const before = await cookies(page, 'before-explicit-refresh');
  record(page, { event: 'request', source: 'explicit-cookie-refresh', method: 'POST', origin: api, path: '/api/auth/token/refresh/', refreshCookiePresent: Boolean(before) });
  const refreshed = await page.request.post(`${api}/api/auth/token/refresh/`, { data: {} });
  await summarize(page, refreshed, 'explicit-cookie-refresh');
  expect(refreshed.ok(), 'Cookie-only refresh').toBeTruthy();
  const pair = await refreshed.json() as { access?: unknown; refresh?: unknown };
  expect(typeof pair.access).toBe('string'); expect(pair.refresh).toBeUndefined();
  const after = await cookies(page, 'after-explicit-refresh');
  const changed = Boolean(before?.value && after?.value && before.value !== after.value);
  record(page, { event: 'refresh-rotation', changed }); expect(changed).toBeTruthy();
  const me = await ownerRead(page, '/api/auth/me/', pair.access as string);
  expect(me.is_merchant_user).toBe(true);
  const leads = await ownerRead(page, '/api/leads/', access);
  expect(Number(leads.count)).toBeGreaterThan(0);
});
test('Product UI login preserves session across hard navigation and reload', async ({ page }) => {
  await uiLogin(page); await hardReloadRoutes(page);
});
test('Existing smoke helper preserves session across hard navigation and reload', async ({ page }) => {
  await existingHelper(page); await hardReloadRoutes(page);
});
test('Seed to owner API to lead DOM visibility', async ({ page }) => {
  const access = await apiLogin(page);
  const me = await ownerRead(page, '/api/auth/me/', access);
  const leads = await ownerRead(page, '/api/leads/', access);
  const seedBusiness = Number(process.env.CRM_DIAGNOSTIC_BUSINESS_ID);
  const seedCount = Number(process.env.CRM_DIAGNOSTIC_LEAD_COUNT);
  expect(Number.isSafeInteger(seedBusiness) && seedBusiness > 0).toBeTruthy();
  expect(seedCount).toBeGreaterThan(0);
  const businessIds = (me.businesses as Array<{id:number}>).map(row => row.id);
  const rows = leads.results as Array<{id:number;business:number}>;
  record(page, { event: 'seed-api-compare', seedBusiness, seedCount, userBusinesses: businessIds, apiCount: leads.count, ids: rows.map(row => row.id) });
  expect(businessIds).toContain(seedBusiness);
  expect(Number(leads.count)).toBe(seedCount);
  expect(rows.every(row => row.business === seedBusiness)).toBeTruthy();
  await uiLogin(page);
  await page.goto('/app/leads');
  await expect(page).toHaveURL(/\/app\/leads\/?$/);
  const visible = page.locator('div[role="button"][tabindex="0"]:visible');
  await expect(visible.first(), 'Seeded lead must be rendered, not a weakened selector').toBeVisible();
  record(page, { event: 'visible-lead-row-count', count: await visible.count() });
});
