import { createHmac } from 'node:crypto';
import { expect, test, type Page } from '@playwright/test';
import { ru } from '../src/lib/i18n/ru';
import { kk } from '../src/lib/i18n/kk';
import { en } from '../src/lib/i18n/en';

test.beforeEach(() => { test.setTimeout(120_000); test.skip(process.env.E2E_PLATFORM_OWNERSHIP !== '1', 'Use verify_platform_ownership.py'); });
const api = process.env.E2E_API_BASE_URL || 'http://127.0.0.1:8000';
function totp(secret: string) {
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
  const bits = secret.replace(/=+$/u, '').split('').map(char => alphabet.indexOf(char).toString(2).padStart(5, '0')).join('');
  const key = Buffer.from((bits.match(/.{8}/g) || []).map(byte => Number.parseInt(byte, 2)));
  const counter = Buffer.alloc(8); counter.writeBigUInt64BE(BigInt(Math.floor(Date.now() / 30_000)));
  const digest = createHmac('sha1', key).update(counter).digest();
  return String((digest.readUInt32BE(digest[digest.length - 1] & 15) & 0x7fffffff) % 1_000_000).padStart(6, '0');
}
async function login(page: Page, project: string, scenario: string, kind: string) {
  await page.goto('/login');
  await page.locator('form input[type=email]').fill(`ownership-${scenario}-${kind}-${project}@example.com`);
  await page.locator('form input[type=password]').fill(process.env.E2E_PASSWORD || 'ZaniTest123!');
  const response = page.waitForResponse(r => r.url().endsWith('/api/auth/token/') && r.request().method() === 'POST');
  await page.locator('form button[type=submit]').click();
  const result = await response; expect(result.ok()).toBeTruthy();
  const headers = { Authorization: `Bearer ${(await result.json()).access}` };
  await expect(page).not.toHaveURL(/\/login/);
  return headers;
}
async function setup(page: Page, project: string, scenario: string) {
  const headers = await login(page, project, scenario, 'admin');
  const businesses = await page.request.get(`${api}/api/platform/merchants/?search=${encodeURIComponent(`Ownership ${scenario} ${project}`)}`, { headers });
  const id = (await businesses.json()).results[0].id;
  const cases = await page.request.get(`${api}/api/platform/support-cases/?business=${id}`, { headers });
  const caseId = (await cases.json()).results[0].id;
  await page.goto('about:blank');
  const start = await page.request.post(`${api}/api/auth/mfa/enrollment/start/`, { headers, data: {} });
  const enrollment = await start.json();
  const confirmed = await page.request.post(`${api}/api/auth/mfa/enrollment/confirm/`, { data: { challenge_token: enrollment.challenge_token, code: totp(enrollment.manual_key) } });
  expect(confirmed.ok()).toBeTruthy();
  const codes: string[] = (await confirmed.json()).recovery_codes;
  const root = `/platform/merchants/${id}?section=ownership`;
  await page.goto(root);
  await expect(page.getByTestId('business-ownership')).toBeVisible();
  return { id, caseId, codes, root };
}
async function fillTerms(page: Page, project: string, scenario: string, caseId: number, disable = false) {
  const form = page.getByTestId('ownership-prepare');
  await form.getByRole('combobox', { name: new RegExp(`^${ru['ownership.newOwner']}`) }).click();
  await page.getByRole('option', { name: new RegExp(`recipient ${scenario} ${project}`) }).click();
  await form.getByRole('combobox', { name: new RegExp(`^${ru['ownership.previousAccess']}`) }).click();
  await page.getByRole('option', { name: disable ? ru['ownership.disableAccess'] : 'Specialist', exact: true }).click();
  await form.locator('[name=support_case_id]').fill(String(caseId));
  await form.getByRole('textbox', { name: ru['supportCases.reason'], exact: true }).fill('Both parties requested the transfer');
  return form;
}
async function confirmDialog(page: Page, label: string) {
  await page.getByRole('dialog').getByRole('button', { name: label, exact: true }).click();
}

test('ownership complete through operator and both personal accounts', async ({ page, browser }, info) => {
  const { id, caseId, codes, root } = await setup(page, info.project.name, 'flow');
  const form = await fillTerms(page, info.project.name, 'flow', caseId, info.project.name.includes('mobile'));
  await page.getByRole('tab', { name: ru['clinicCrm.tab.state'], exact: true }).click();
  await confirmDialog(page, ru['taskWorkspace.keepEditing']);
  await expect(form.locator('[name=support_case_id]')).toHaveValue(String(caseId));
  await form.locator('[name=mfa]').fill('wrong');
  await form.getByRole('button', { name: ru['ownership.prepare'], exact: true }).click();
  await expect(page.getByText(ru['businessDetails.mfaError'], { exact: true })).toBeVisible();
  await expect(form.getByRole('textbox', { name: ru['supportCases.reason'], exact: true })).toHaveValue('Both parties requested the transfer');
  await form.locator('[name=mfa]').fill(codes[0]);
  const prepared = page.waitForResponse(r => r.url().endsWith(`/merchants/${id}/ownership/`) && r.request().method() === 'POST');
  await form.getByRole('button', { name: ru['ownership.prepare'], exact: true }).click();
  const preparedResponse = await prepared; expect(preparedResponse.status()).toBe(200);
  await expect(page.getByTestId('ownership-request')).toBeVisible();
  await expect(page.getByRole('button', { name: ru['ownership.execute'], exact: true })).toHaveCount(0);
  const ownerContext = await browser.newContext({ baseURL: new URL(page.url()).origin, viewport: page.viewportSize()! });
  const recipientContext = await browser.newContext({ baseURL: new URL(page.url()).origin, viewport: page.viewportSize()! });
  try {
    for (const [context, kind] of [[ownerContext, 'owner'], [recipientContext, 'recipient']] as const) {
      const participantPage = await context.newPage();
      await login(participantPage, info.project.name, 'flow', kind);
      await participantPage.goto('/account');
      const request = participantPage.getByTestId('ownership-request');
      await expect(request).toBeVisible();
      await request.getByRole('button', { name: ru['ownership.confirm'], exact: true }).click();
      await confirmDialog(participantPage, ru['ownership.confirm']);
      await expect(request.getByRole('button', { name: ru['ownership.confirm'], exact: true })).toHaveCount(0);
      await participantPage.screenshot({ path: info.outputPath(`ownership-${kind}.png`), fullPage: true });
    }
    await page.getByTestId('business-ownership').getByRole('button', { name: ru['common.refresh'], exact: true }).click();
    await expect(page.getByRole('button', { name: ru['ownership.execute'], exact: true })).toBeVisible();
    await form.locator('[name=mfa]').fill(codes[1]);
    await page.getByRole('button', { name: ru['ownership.execute'], exact: true }).click();
    await confirmDialog(page, ru['ownership.execute']);
    await expect(page.getByTestId('ownership-request')).toContainText(ru['ownership.status.completed']);
    await page.reload();
    await expect(page.getByTestId('ownership-request')).toContainText(ru['ownership.status.completed']);
    await expect(page.getByTestId('clinic-identity')).toContainText(`recipient flow ${info.project.name}`);
    await expect(page.getByRole('button', { name: ru['ownership.execute'], exact: true })).toHaveCount(0);
    await page.screenshot({ path: info.outputPath('ownership-completed.png'), fullPage: true });
    for (const context of [ownerContext, recipientContext]) {
      const participantPage = context.pages()[0];
      await participantPage.reload();
      await expect(participantPage).toHaveURL(/\/login/);
    }
    expect(page.url()).toContain(root);
  } finally { await ownerContext.close(); await recipientContext.close(); }
});

test('ownership load recovery locales keyboard manager denial and participant decline', async ({ page, browser }, info) => {
  const { id, caseId, codes, root } = await setup(page, info.project.name, 'states');
  const pattern = `**/api/platform/merchants/${id}/ownership/`;
  await page.route(pattern, route => route.fulfill({ status: 503, json: { code: 'temporary_service_failure', category: 'temporary' } }));
  await page.reload(); await expect(page.getByRole('alert').first()).toBeVisible();
  await expect(page.getByTestId('ownership-prepare')).toHaveCount(0);
  await page.unroute(pattern);
  await page.getByRole('button', { name: ru['platform.merchantDetail.refresh'], exact: true }).click();
  for (const [language, copy] of [['ru', ru], ['kk', kk], ['en', en]] as const) {
    await page.evaluate(value => localStorage.setItem('ai_smb_language', value), language);
    await page.goto(root);
    const recipient = page.getByRole('combobox', { name: new RegExp(`^${copy['ownership.newOwner']}`) });
    await expect(recipient).toBeVisible(); await recipient.focus(); await page.keyboard.press('Tab');
    await expect(page.getByRole('combobox', { name: new RegExp(`^${copy['ownership.previousAccess']}`) })).toBeFocused();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBeTruthy();
    await page.screenshot({ path: info.outputPath(`ownership-${language}.png`), fullPage: true });
  }
  await page.evaluate(() => localStorage.setItem('ai_smb_language', 'ru')); await page.goto(root);
  const form = await fillTerms(page, info.project.name, 'states', caseId);
  await form.locator('[name=mfa]').fill(codes[0]);
  await form.getByRole('button', { name: ru['ownership.prepare'], exact: true }).click();
  await expect(page.getByTestId('ownership-request')).toBeVisible();
  const context = await browser.newContext({ baseURL: new URL(page.url()).origin, viewport: page.viewportSize()! });
  try {
    const managerPage = await context.newPage();
    await login(managerPage, info.project.name, 'states', 'manager');
    await managerPage.goto(root);
    await expect(managerPage.getByTestId('ownership-request')).toBeVisible();
    await expect(managerPage.getByTestId('ownership-prepare')).toHaveCount(0);
    await expect(managerPage.getByRole('button', { name: ru['ownership.cancel'], exact: true })).toHaveCount(0);
  } finally { await context.close(); }
  const recipientContext = await browser.newContext({ baseURL: new URL(page.url()).origin, viewport: page.viewportSize()! });
  try {
    const recipientPage = await recipientContext.newPage();
    await login(recipientPage, info.project.name, 'states', 'recipient'); await recipientPage.goto('/account');
    await recipientPage.getByRole('button', { name: ru['ownership.decline'], exact: true }).click();
    await confirmDialog(recipientPage, ru['ownership.decline']);
    await expect(recipientPage.getByTestId('ownership-request')).toContainText(ru['ownership.status.cancelled']);
    await page.getByTestId('business-ownership').getByRole('button', { name: ru['common.refresh'], exact: true }).click();
    await expect(page.getByTestId('ownership-request')).toContainText(ru['ownership.status.cancelled']);
  } finally { await recipientContext.close(); }
  await page.route(pattern, route => route.fulfill({ status: 403, json: { code: 'permission_denied', category: 'permission' } }));
  await page.reload();
  await expect(page.getByTestId('permission-fallback')).toBeVisible();
  await expect(page.getByTestId('ownership-prepare')).toHaveCount(0);
});
