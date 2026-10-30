import { authPost } from "./support/auth-request";
import { createHmac } from 'node:crypto';
import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { expect, test, type Page } from '@playwright/test';
import { ru } from '../src/lib/i18n/ru';
import { kk } from '../src/lib/i18n/kk';
import { en } from '../src/lib/i18n/en';

test.beforeEach(() => { test.setTimeout(120_000); test.skip(process.env.E2E_PLATFORM_RECOVERY !== '1', 'Use verify_platform_recovery.py'); });
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
  await page.locator('form input[type=email]').fill(`recovery-${scenario}-${kind}-${project}@example.com`);
  await page.locator('form input[type=password]').fill(process.env.E2E_PASSWORD || 'ZaniTest123!');
  const response = page.waitForResponse(r => r.url().endsWith('/api/auth/token/') && r.request().method() === 'POST');
  await page.locator('form button[type=submit]').click();
  const result = await response; expect(result.ok()).toBeTruthy();
  await expect(page).not.toHaveURL(/\/login/);
  return { Authorization: `Bearer ${(await result.json()).access}` };
}
async function setup(page: Page, project: string, scenario: string) {
  const headers = await login(page, project, scenario, 'operator');
  const businesses = await page.request.get(`${api}/api/platform/merchants/?search=${encodeURIComponent(`Recovery ${scenario} ${project}`)}`, { headers });
  const id = (await businesses.json()).results[0].id;
  const cases = await page.request.get(`${api}/api/platform/support-cases/?business=${id}`, { headers });
  const rows = (await cases.json()).results as { id: number; subject: string }[];
  await page.goto('about:blank');
  const start = await page.request.post(`${api}/api/auth/mfa/enrollment/start/`, { headers, data: {} });
  const enrollment = await start.json();
  const confirmed = await authPost(page.request, `${api}/api/auth/mfa/enrollment/confirm/`, { data: { challenge_token: enrollment.challenge_token, code: totp(enrollment.manual_key) } });
  expect(confirmed.ok()).toBeTruthy();
  const codes: string[] = (await confirmed.json()).recovery_codes;
  const root = `/platform/merchants/${id}?section=recovery`;
  await page.goto(root);
  await expect(page.getByTestId('business-recovery')).toBeVisible();
  return { id, rows, codes, root };
}
async function fill(page: Page, project: string, scenario: string, kind: string, caseId: number) {
  const form = page.getByTestId('recovery-prepare');
  await form.getByRole('combobox', { name: new RegExp(`^${ru['recovery.account']}`) }).click();
  await page.getByRole('option', { name: new RegExp(`${kind} ${scenario} ${project}`) }).click();
  await form.locator('[name=new_email]').fill(`restored-${scenario}-${project}@example.com`);
  await form.locator('[name=support_case_id]').fill(String(caseId));
  await form.getByRole('textbox', { name: ru['supportCases.reason'], exact: true }).fill('Account holder requested recovery through support');
  if (kind === 'owner') {
    await form.getByRole('textbox', { name: ru['recovery.reference'], exact: true }).fill('Previously verified onboarding reference 42, authority matched');
    await form.getByRole('checkbox').check();
  }
  return form;
}
async function dialog(page: Page, label: string) {
  await page.getByRole('dialog').getByRole('button', { name: label, exact: true }).click();
}

test('recovery employee confirmation transport and public completion', async ({ page, browser }, info) => {
  const { id, rows, codes } = await setup(page, info.project.name, 'flow');
  const form = await fill(page, info.project.name, 'flow', 'employee', rows.find(row => row.subject === 'Recover employee')!.id);
  await form.getByRole('button', { name: ru['supportCases.create'], exact: true }).click();
  const support = page.getByTestId('support-create-dialog');
  await support.getByRole('textbox', { name: ru['supportCases.subject'], exact: true }).fill('Account recovery by email');
  await support.getByRole('textbox', { name: ru['supportCases.description'], exact: true }).fill('Employee contacted support after losing all access');
  const created = page.waitForResponse(r => r.url().includes('/api/platform/support-cases/') && r.request().method() === 'POST');
  await support.getByRole('button', { name: ru['supportCases.submit'], exact: true }).click();
  const caseResponse = await created; expect(caseResponse.status()).toBe(201);
  await expect(form.locator('[name=support_case_id]')).toHaveValue(String((await caseResponse.json()).id));
  await form.locator('[name=mfa]').fill('wrong');
  await form.getByRole('button', { name: ru['recovery.prepare'], exact: true }).click();
  await expect(page.getByText(ru['businessDetails.mfaError'], { exact: true })).toBeVisible();
  await expect(form.getByRole('textbox', { name: ru['supportCases.reason'], exact: true })).toHaveValue('Account holder requested recovery through support');
  await form.locator('[name=mfa]').fill(codes[0]);
  await form.getByRole('button', { name: ru['recovery.prepare'], exact: true }).click();
  const row = page.getByTestId('recovery-request');
  await expect(row).toBeVisible();
  await expect(row.getByRole('button', { name: ru['recovery.send'], exact: true })).toBeDisabled();
  const ownerContext = await browser.newContext({ baseURL: new URL(page.url()).origin, viewport: page.viewportSize()! });
  const claimantContext = await browser.newContext({ baseURL: new URL(page.url()).origin, viewport: page.viewportSize()! });
  try {
    const ownerPage = await ownerContext.newPage();
    await login(ownerPage, info.project.name, 'flow', 'owner');
    await ownerPage.goto('/account');
    const confirmation = ownerPage.getByTestId('recovery-confirmations');
    await expect(confirmation).toBeVisible();
    await confirmation.getByRole('button', { name: ru['ownership.confirm'], exact: true }).click();
    await dialog(ownerPage, ru['ownership.confirm']);
    await expect(confirmation).toHaveCount(0);
    await page.getByTestId('business-recovery').getByRole('button', { name: ru['common.refresh'], exact: true }).click();
    await form.locator('[name=mfa]').fill(codes[1]);
    await row.getByRole('button', { name: ru['recovery.send'], exact: true }).click();
    await dialog(page, ru['recovery.send']);
    await expect(row).toContainText(ru['recovery.delivery.accepted']);
    const directory = process.env.E2E_RECOVERY_MAIL_DIR!;
    const mail = readdirSync(directory).map(file => JSON.parse(readFileSync(join(directory, file), 'utf8')) as { to: string[]; body: string }).find(item => item.to.includes(`restored-flow-${info.project.name}@example.com`))!;
    const link = mail.body.match(/http[^\s]+/)![0];
    const claimant = await claimantContext.newPage();
    await claimant.goto(link);
    await expect(claimant).toHaveURL(/\/recover-account$/);
    await claimant.getByLabel(ru['invite.newPassword'], { exact: true }).fill('RecoveredPass123!');
    await claimant.getByLabel(ru['passwordReset.repeatPassword'], { exact: true }).fill('RecoveredPass123!');
    await claimant.getByRole('button', { name: ru['recovery.complete'], exact: true }).click();
    await expect(claimant.getByText(ru['recovery.done'], { exact: true })).toBeVisible();
    await claimant.screenshot({ path: info.outputPath('recovery-completed.png'), fullPage: true });
    await claimant.getByRole('link', { name: ru['passwordReset.backToLogin'] }).click();
    await claimant.locator('form input[type=email]').fill(`restored-flow-${info.project.name}@example.com`);
    await claimant.locator('form input[type=password]').fill('RecoveredPass123!');
    await claimant.locator('form button[type=submit]').click();
    await expect(claimant).toHaveURL(/\/app/);
    await page.getByTestId('business-recovery').getByRole('button', { name: ru['common.refresh'], exact: true }).click();
    await expect(row).toContainText(ru['recovery.status.completed']);
    await page.screenshot({ path: info.outputPath('operator-completed.png'), fullPage: true });
    expect(page.url()).toContain(`/merchants/${id}`);
  } finally { await ownerContext.close(); await claimantContext.close(); }
});

test('recovery owner evidence draft error recovery locales and contact', async ({ page }, info) => {
  const { rows, codes, root } = await setup(page, info.project.name, 'states');
  await expect(page.getByText(ru['recovery.empty'], { exact: true })).toBeVisible();
  const form = await fill(page, info.project.name, 'states', 'owner', rows.find(row => row.subject === 'Recover owner')!.id);
  await page.getByRole('tab', { name: ru['clinicCrm.tab.state'], exact: true }).click();
  await dialog(page, ru['taskWorkspace.keepEditing']);
  await expect(form.locator('[name=new_email]')).toHaveValue(`restored-states-${info.project.name}@example.com`);
  await form.getByRole('checkbox').uncheck();
  await form.locator('[name=mfa]').fill(codes[0]);
  await expect(form.getByRole('button', { name: ru['recovery.prepare'], exact: true })).toBeDisabled();
  await form.getByRole('checkbox').check();
  await form.getByRole('button', { name: ru['recovery.prepare'], exact: true }).click();
  await expect(page.getByTestId('recovery-request')).toBeVisible();
  for (const [language, dictionary] of [['kk', kk], ['en', en]] as const) {
    await page.evaluate(lang => localStorage.setItem('ai_smb_language', lang), language);
    await page.reload();
    await expect(page.getByRole('heading', { name: dictionary['recovery.title'], exact: true })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBeTruthy();
    await page.screenshot({ path: info.outputPath(`recovery-${language}.png`), fullPage: true });
  }
  await page.evaluate(() => localStorage.setItem('ai_smb_language', 'ru'));
  await page.route('**/account-recovery/', route => route.request().method() === 'GET' ? route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ code: 'temporary_service_failure', category: 'temporary' }) }) : route.continue());
  await page.goto(root);
  await expect(page.getByTestId('business-recovery')).toHaveCount(0);
  await page.unroute('**/account-recovery/');
  await page.getByRole('button', { name: ru['platform.merchantDetail.refresh'], exact: true }).click();
  await expect(page.getByTestId('business-recovery')).toBeVisible();
  await page.route('**/account-recovery/', route => route.fulfill({ status: 403, contentType: 'application/json', body: JSON.stringify({ code: 'permission_denied', category: 'permission' }) }));
  await page.reload();
  await expect(page.getByTestId('business-recovery')).toHaveCount(0);
  await page.unroute('**/account-recovery/');
  await page.goto('/recover-account');
  const contact = page.getByRole('link', { name: 'support@example.com', exact: true });
  await expect(contact).toHaveAttribute('href', 'mailto:support@example.com');
  await contact.focus(); await expect(contact).toBeFocused();
});
