import { createHmac } from 'node:crypto';
import { expect, test, type Page } from '@playwright/test';
import { ru } from '../src/lib/i18n/ru';
import { kk } from '../src/lib/i18n/kk';
import { en } from '../src/lib/i18n/en';

test.beforeEach(() => { test.setTimeout(90_000); test.skip(process.env.E2E_PLATFORM_DETAILS !== '1', 'Use verify_platform_details.py'); });
const api = process.env.E2E_API_BASE_URL || 'http://127.0.0.1:8000';
function totp(secret: string) {
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
  const bits = secret.replace(/=+$/u, '').split('').map(char => alphabet.indexOf(char).toString(2).padStart(5, '0')).join('');
  const key = Buffer.from((bits.match(/.{8}/g) || []).map(byte => Number.parseInt(byte, 2)));
  const counter = Buffer.alloc(8); counter.writeBigUInt64BE(BigInt(Math.floor(Date.now() / 30_000)));
  const digest = createHmac('sha1', key).update(counter).digest();
  return String((digest.readUInt32BE(digest[digest.length - 1] & 15) & 0x7fffffff) % 1_000_000).padStart(6, '0');
}
async function open(page: Page, project: string, role: string, enroll = false) {
  await page.goto('/login');
  await page.locator('form input[type=email]').fill(`details-${role}-${project}@example.com`);
  await page.locator('form input[type=password]').fill(process.env.E2E_PASSWORD || 'ZaniTest123!');
  const login = page.waitForResponse(r => r.url().endsWith('/api/auth/token/') && r.request().method() === 'POST');
  await page.locator('form button[type=submit]').click();
  const headers = { Authorization: `Bearer ${(await (await login).json()).access}` };
  await expect(page).toHaveURL(/\/platform/);
  const businesses = await page.request.get(`${api}/api/platform/merchants/?search=${encodeURIComponent(`Details ${role} ${project}`)}`, { headers });
  const id = (await businesses.json()).results[0].id;
  const cases = await page.request.get(`${api}/api/platform/support-cases/?business=${id}`, { headers });
  const caseId = (await cases.json()).results[0].id;
  let codes: string[] = [];
  if (enroll) {
    // Stop authenticated polling before enrollment rotates the session epoch.
    await page.goto('about:blank');
    const started = await page.request.post(`${api}/api/auth/mfa/enrollment/start/`, { headers, data: {} });
    const enrollment = await started.json();
    const confirmed = await page.request.post(`${api}/api/auth/mfa/enrollment/confirm/`, { data: { challenge_token: enrollment.challenge_token, code: totp(enrollment.manual_key) } });
    expect(confirmed.ok()).toBeTruthy(); codes = (await confirmed.json()).recovery_codes;
  }
  const root = `/platform/merchants/${id}?section=details`;
  await page.goto(root);
  await expect(page.getByTestId('business-details-form')).toBeVisible();
  return { id, root, caseId, codes };
}

test('details save with real MFA retains errors and prevents stale overwrite', async ({ page }, info) => {
  const { id, caseId, codes } = await open(page, info.project.name, 'platform_manager', true);
  const form = page.getByTestId('business-details-form');
  await form.locator('[name=name]').fill('Corrected business');
  await form.locator('[name=phone]').fill('');
  await form.locator('[name=support_case_id]').fill(String(caseId));
  await form.getByLabel(ru['supportCases.reason'], { exact: true }).fill('Requested detail correction');
  await form.locator('[name=mfa]').fill('invalid');
  await form.getByRole('button', { name: ru['common.save'], exact: true }).click();
  await expect(form.getByRole('alert').first()).toBeVisible();
  await expect(form.locator('[name=name]')).toHaveValue('Corrected business');
  await expect(form.locator('[name=mfa]')).toHaveValue('');
  await form.locator('[name=mfa]').fill(codes[0]);
  const saved = page.waitForResponse(r => r.url().endsWith(`/merchants/${id}/details/`) && r.request().method() === 'PATCH');
  await form.getByRole('button', { name: ru['common.save'], exact: true }).click();
  const savedResponse = await saved;
  expect(savedResponse.status()).toBe(200);
  const writeHeaders = savedResponse.request().headers();
  await expect(form.getByText(ru['common.saved'], { exact: true })).toBeVisible();
  await expect(form.locator('[name=phone]')).toHaveValue('');
  await page.reload(); await expect(form.locator('[name=name]')).toHaveValue('Corrected business');
  await form.locator('[name=city]').fill('Draft city');
  await page.getByRole('tab', { name: ru['clinicCrm.tab.state'], exact: true }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.getByRole('button', { name: ru['taskWorkspace.keepEditing'], exact: true }).click();
  await expect(form.locator('[name=city]')).toHaveValue('Draft city');
  await form.locator('[name=support_case_id]').fill(String(caseId));
  await form.getByLabel(ru['supportCases.reason'], { exact: true }).fill('City correction');
  await form.locator('[name=mfa]').fill(codes[1]);
  const current = await page.request.get(`${api}/api/platform/merchants/${id}/details/`, { headers: writeHeaders });
  const concurrent = await page.request.patch(`${api}/api/platform/merchants/${id}/details/`, { headers: writeHeaders,
    data: { changes: { city: 'Concurrent city' }, expected_revision: (await current.json()).revision, support_case_id: caseId, reason: 'Concurrent correction' } });
  expect(concurrent.status()).toBe(200);
  await form.getByRole('button', { name: ru['common.save'], exact: true }).click();
  await expect(form.getByText(ru['businessDetails.conflict'])).toBeVisible();
  await expect(form.locator('[name=city]')).toHaveValue('Draft city');
  await expect(form.getByRole('button', { name: ru['common.save'], exact: true })).toBeDisabled();
  await form.getByRole('button', { name: ru['common.refresh'], exact: true }).click();
  await page.getByRole('button', { name: ru['taskWorkspace.discard'], exact: true }).click();
  await expect(form.locator('[name=city]')).toHaveValue('Concurrent city');
  await expect(form.getByText(ru['businessDetails.conflict'])).toHaveCount(0);
  await page.getByRole('tab', { name: ru['clinicCrm.tab.access'], exact: true }).click();
  await expect(page.getByTestId('clinic-access-history')).toContainText('Concurrent correction');
  await expect(page.getByTestId('clinic-access-history').getByRole('link', { name: `${ru['businessDetails.caseId']} #${caseId}`, exact: true }).first()).toHaveAttribute('href', `/platform/support/${caseId}`);
  // Acceptance chain: completed action -> audit -> support case -> same business
  // -> each diagnosis/action surface, without relying on a manually typed deep link.
  await page.getByTestId('clinic-access-history').getByRole('link', { name: `${ru['businessDetails.caseId']} #${caseId}`, exact: true }).first().click();
  await expect(page).toHaveURL(new RegExp(`/platform/support/${caseId}$`));
  await page.getByTestId('support-case-context').getByRole('link', { name: 'Corrected business', exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/platform/merchants/${id}$`));
  for (const [section, testId] of [['details', 'business-details-form'], ['ownership', 'business-ownership'], ['recovery', 'business-recovery'], ['employees', 'business-employee-access'], ['billing', 'platform-billing']] as const) {
    await page.getByRole('tab', { name: ru[`clinicCrm.tab.${section}`], exact: true }).click();
    await expect(page.getByTestId(testId)).toBeVisible();
    await expect(page).toHaveURL(new RegExp(`/platform/merchants/${id}\\?section=${section}$`));
  }
  await page.getByRole('tab', { name: ru['clinicCrm.tab.access'], exact: true }).click();
  for (const [language, copy] of [['ru', ru], ['kk', kk], ['en', en]] as const) {
    await page.evaluate(value => localStorage.setItem('ai_smb_language', value), language);await page.reload();
    for (const section of ['ownership', 'recovery', 'employees', 'billing']) {
      await expect(page.getByTestId('clinic-access-history')).toContainText(copy[`clinicCrm.tab.${section}`]);
    }
    await expect(page.getByTestId('clinic-access-history')).not.toContainText(/clinicCrm\.(kind|section)\./);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBeTruthy();
    await page.screenshot({ path: info.outputPath(`admin-history-${language}.png`), fullPage: true });
  }
});

test('details load recovery forbidden and localized keyboard form', async ({ page }, info) => {
  const { id, root } = await open(page, info.project.name, 'platform_admin');
  const path = `**/api/platform/merchants/${id}/details/`;
  await page.route(path, route => route.fulfill({ status: 503, json: { code: 'temporary_service_failure', category: 'temporary' } }));
  await page.reload();
  await expect(page.getByTestId('business-details-form')).toHaveCount(0);
  await expect(page.getByRole('alert').first()).toBeVisible();
  await page.unroute(path);
  await page.getByRole('button', { name: ru['platform.merchantDetail.refresh'], exact: true }).click();
  await expect(page.getByTestId('business-details-form')).toBeVisible();
  for (const [language, copy] of [['ru', ru], ['kk', kk], ['en', en]] as const) {
    await page.evaluate(value => localStorage.setItem('ai_smb_language', value), language);
    await page.goto(root);
    const name = page.getByLabel(copy['businessForm.name'], { exact: true });
    await expect(name).toBeVisible(); await name.focus(); await page.keyboard.press('Tab');
    await expect(page.getByLabel(copy['businessForm.legalName'], { exact: true })).toBeFocused();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBeTruthy();
    await page.screenshot({ path: info.outputPath(`business-details-${language}.png`), fullPage: true });
  }
  await page.route(path, route => route.fulfill({ status: 403, json: { code: 'permission_denied', category: 'permission' } }));
  await page.reload();
  await expect(page.getByTestId('permission-fallback')).toBeVisible();
  await expect(page.getByTestId('business-details-form')).toHaveCount(0);
});
