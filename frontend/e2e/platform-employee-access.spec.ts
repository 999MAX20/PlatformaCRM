import { authPost } from "./support/auth-request";
import { createHmac } from 'node:crypto';
import { expect, test, type Page } from '@playwright/test';
import { ru } from '../src/lib/i18n/ru';
import { kk } from '../src/lib/i18n/kk';
import { en } from '../src/lib/i18n/en';

test.beforeEach(() => { test.setTimeout(150_000); test.skip(process.env.E2E_PLATFORM_EMPLOYEE_ACCESS !== '1', 'Use verify_platform_employee_access.py'); });
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
  await page.locator('form input[type=email]').fill(`access-${scenario}-${kind}-${project}@example.com`);
  await page.locator('form input[type=password]').fill(process.env.E2E_PASSWORD || 'ZaniTest123!');
  const response = page.waitForResponse(r => r.url().endsWith('/api/auth/token/') && r.request().method() === 'POST');
  await page.locator('form button[type=submit]').click();
  const result = await response; expect(result.ok()).toBeTruthy();
  await expect(page).not.toHaveURL(/\/login/);
  return { Authorization: `Bearer ${(await result.json()).access}` };
}
async function setup(page: Page, project: string, scenario: string) {
  const headers = await login(page, project, scenario, 'operator');
  const businesses = await page.request.get(`${api}/api/platform/merchants/?search=${encodeURIComponent(`Access ${scenario} ${project}`)}`, { headers });
  const id = (await businesses.json()).results.find((row: { name: string }) => row.name === `Access ${scenario} ${project}`).id;
  const cases = await page.request.get(`${api}/api/platform/support-cases/?business=${id}`, { headers });
  const caseId = (await cases.json()).results[0].id;
  await page.goto('about:blank');
  const start = await page.request.post(`${api}/api/auth/mfa/enrollment/start/`, { headers, data: {} });
  const enrollment = await start.json();
  const confirmed = await authPost(page.request, `${api}/api/auth/mfa/enrollment/confirm/`, { data: { challenge_token: enrollment.challenge_token, code: totp(enrollment.manual_key) } });
  expect(confirmed.ok()).toBeTruthy();
  const codes: string[] = (await confirmed.json()).recovery_codes;
  const root = `/platform/merchants/${id}?section=employees`;
  await page.goto(root);
  await expect(page.getByTestId('business-employee-access')).toBeVisible();
  return { id, caseId, codes, root, headers };
}
async function pick(page: Page, label: string, option: string) {
  await page.getByRole('combobox', { name: new RegExp(`^${label}`) }).click();
  await page.getByRole('option', { name: option, exact: true }).click();
}
async function dialog(page: Page, label: string) { await page.getByRole('dialog').getByRole('button', { name: label, exact: true }).click(); }
async function fill(page: Page, project: string, scenario: string, action: string, caseId: number, recipient = 'employee') {
  await page.getByTestId('business-employee-access').getByRole('button', { name: new RegExp(`${recipient} ${scenario}${recipient === 'employee' ? ` ${project}` : ''}`) }).click();
  await expect(page.getByTestId('access-diagnostics')).toBeVisible();
  await pick(page, ru['employeeAccess.action'], ru[`employeeAccess.action.${action}`]);
  const form = page.getByTestId('access-prepare');
  await form.locator('[name=support_case_id]').fill(String(caseId));
  await form.getByRole('textbox', { name: ru['supportCases.reason'], exact: true }).fill('Verified employee access request');
  return form;
}
async function prepare(page: Page, code: string) {
  const form = page.getByTestId('access-prepare');
  await form.locator('[name=mfa]').fill(code);
  const response = page.waitForResponse(r => /\/employee-access\/$/.test(r.url()) && r.request().method() === 'POST');
  await form.getByRole('button', { name: ru['employeeAccess.prepare'], exact: true }).click();
  const result = await response; expect(result.status()).toBe(200);
  const id = (await result.json()).id;
  await expect(page.locator(`[data-request-id="${id}"]`)).toBeVisible();
  return id as string;
}
async function execute(page: Page, id: string, code: string) {
  await page.getByTestId('access-prepare').locator('[name=mfa]').fill(code);
  const row = page.locator(`[data-request-id="${id}"]`);
  await row.getByRole('button', { name: ru['employeeAccess.execute'], exact: true }).click();
  await dialog(page, ru['employeeAccess.execute']);
  await expect(row).toContainText(ru['employeeAccess.status.completed']);
}
async function consent(owner: Page, page: Page) {
  await owner.goto('/account');
  const row = owner.getByTestId('employee-access-confirmations');
  await expect(row).toBeVisible();
  await row.getByRole('button', { name: ru['ownership.confirm'], exact: true }).click();
  await dialog(owner, ru['ownership.confirm']);
  await expect(row).toHaveCount(0);
  await page.getByTestId('business-employee-access').getByRole('button', { name: ru['common.refresh'], exact: true }).click();
}
async function snapshot(page: Page) {
  // Enrollment rotates the login session; inspect the actual UI-authenticated GET.
  const response = page.waitForResponse(r => r.url().includes('/employee-access/?') && r.request().method() === 'GET');
  await page.getByTestId('business-employee-access').getByRole('button', { name: ru['common.refresh'], exact: true }).click();
  const result = await response; expect(result.status()).toBe(200);
  return result.json();
}

test('employee access disable restore role and owner consent', async ({ page, browser }, info) => {
  const { caseId, codes } = await setup(page, info.project.name, 'flow');
  const ownerContext = await browser.newContext({ baseURL: new URL(page.url()).origin, viewport: page.viewportSize()! });
  try {
    const owner = await ownerContext.newPage(); await login(owner, info.project.name, 'flow', 'owner');
    await fill(page, info.project.name, 'flow', 'disable', caseId);
    await expect(page.getByTestId('access-diagnostics')).toContainText('Preserved specialist');
    const disabled = await prepare(page, codes[0]); await execute(page, disabled, codes[1]);
    let state = await snapshot(page);
    let employee = state.members.find((row: { email: string }) => row.email.includes('-employee-'));
    expect(employee.membership_active).toBe(false); expect(employee.account_active).toBe(true);
    expect(employee.specialists[0].is_active).toBe(true); expect(employee.dependencies.tasks).toBe(1);
    await fill(page, info.project.name, 'flow', 'restore', caseId);
    // Disabled employees use the existing owner-requested support-case path.
    await page.getByTestId('access-prepare').getByRole('button', { name: ru['supportCases.create'], exact: true }).click();
    const support = page.getByTestId('support-create-dialog');
    await support.getByRole('textbox', { name: ru['supportCases.subject'], exact: true }).fill('Restore employee access');
    await support.getByRole('textbox', { name: ru['supportCases.description'], exact: true }).fill('Owner requests restoration of business membership');
    await support.getByRole('button', { name: ru['supportCases.submit'], exact: true }).click();
    await expect(support).toHaveCount(0);
    const restored = await prepare(page, codes[2]);
    await expect(page.locator(`[data-request-id="${restored}"]`).getByRole('button', { name: ru['employeeAccess.execute'], exact: true })).toBeDisabled();
    await consent(owner, page); await execute(page, restored, codes[3]);
    await fill(page, info.project.name, 'flow', 'role', caseId); await pick(page, ru['employeeAccess.newRole'], 'Manager');
    const changed = await prepare(page, codes[4]); await consent(owner, page); await execute(page, changed, codes[5]);
    state = await snapshot(page);
    employee = state.members.find((row: { email: string }) => row.email.includes('-employee-'));
    expect(employee.membership_active).toBe(true); expect(employee.role).toBe('manager');
    await page.screenshot({ path: info.outputPath('employee-access-completed.png'), fullPage: true });
  } finally { await ownerContext.close(); }
});

test('employee invitations reissue accept and revoke', async ({ page, browser }, info) => {
  const { id, caseId, codes } = await setup(page, info.project.name, 'invitations');
  const ownerContext = await browser.newContext({ baseURL: new URL(page.url()).origin, viewport: page.viewportSize()! });
  const publicContext = await browser.newContext({ baseURL: new URL(page.url()).origin, viewport: page.viewportSize()! });
  try {
    const owner = await ownerContext.newPage(); const headers = await login(owner, info.project.name, 'invitations', 'owner');
    const invitations = async () => (await (await owner.request.get(`${api}/api/team/invitations/?business=${id}`, { headers })).json()).results as { id: number; email: string; token: string; invite_path: string }[];
    const old = (await invitations()).find(row => row.email.includes('-invite-'))!;
    await pick(page, ru['employeeAccess.records'], ru['employeeAccess.invitations']);
    await fill(page, info.project.name, 'invitations', 'reissue', caseId, 'invite');
    const reissued = await prepare(page, codes[0]); await consent(owner, page); await execute(page, reissued, codes[1]);
    await expect(page.locator(`[data-request-id="${reissued}"]`)).toContainText(ru['employeeAccess.linkReady']);
    const fresh = (await invitations()).find(row => row.id === old.id)!;
    expect(fresh.token).not.toBe(old.token);
    const guest = await publicContext.newPage();
    const invalid = await guest.request.post(`${api}/api/team/invitations/accept/`, { data: { token: old.token, password: 'InvitationPassword123!' } });
    expect(invalid.status()).toBe(400);
    await guest.goto(fresh.invite_path);
    await guest.getByLabel(ru['invite.newPassword'], { exact: true }).fill('InvitationPassword123!');
    await guest.getByLabel(ru['passwordReset.repeatPassword'], { exact: true }).fill('InvitationPassword123!');
    const accepted = guest.waitForResponse(r => r.url().includes('/team/invitations/accept/') && r.request().method() === 'POST');
    await guest.locator('form button[type=submit]').click();
    expect((await accepted).status()).toBe(200);
    await expect(guest).toHaveURL(/\/login$/);
    await page.getByTestId('business-employee-access').getByRole('button', { name: ru['common.refresh'], exact: true }).click();
    await fill(page, info.project.name, 'invitations', 'revoke', caseId, 'revoke');
    const revoked = await prepare(page, codes[2]); await execute(page, revoked, codes[3]);
    await page.screenshot({ path: info.outputPath('employee-invitations-completed.png'), fullPage: true });
  } finally { await ownerContext.close(); await publicContext.close(); }
});

test('employee access drafts errors empty recovery and translated screens', async ({ page }, info) => {
  const { caseId, codes, root } = await setup(page, info.project.name, 'states');
  await expect(page.getByText(ru['employeeAccess.noRequests'], { exact: true })).toBeVisible();
  const form = await fill(page, info.project.name, 'states', 'disable', caseId);
  await page.getByRole('tab', { name: ru['clinicCrm.tab.state'], exact: true }).click();
  await dialog(page, ru['taskWorkspace.keepEditing']);
  await expect(form.getByRole('textbox', { name: ru['supportCases.reason'], exact: true })).toHaveValue('Verified employee access request');
  await form.locator('[name=mfa]').fill('wrong');
  await form.getByRole('button', { name: ru['employeeAccess.prepare'], exact: true }).click();
  await expect(page.getByText(ru['businessDetails.mfaError'], { exact: true })).toBeVisible();
  await expect(form.getByRole('textbox', { name: ru['supportCases.reason'], exact: true })).toHaveValue('Verified employee access request');
  await page.route('**/employee-access/', route => route.request().method() === 'POST' ? route.fulfill({ status: 409, contentType: 'application/json', body: JSON.stringify({ code: 'request_conflict', category: 'conflict' }) }) : route.continue());
  await form.locator('[name=mfa]').fill(codes[0]);
  await form.getByRole('button', { name: ru['employeeAccess.prepare'], exact: true }).click();
  await expect(page.getByText(ru['employeeAccess.conflict'], { exact: true })).toBeVisible();
  await expect(form.getByRole('button', { name: ru['employeeAccess.prepare'], exact: true })).toBeDisabled();
  await page.unroute('**/employee-access/');
  await page.getByTestId('business-employee-access').getByRole('button', { name: ru['common.refresh'], exact: true }).click();
  await dialog(page, ru['taskWorkspace.discard']);
  for (const [language, dictionary] of [['ru', ru], ['kk', kk], ['en', en]] as const) {
    await page.evaluate(lang => localStorage.setItem('ai_smb_language', lang), language); await page.reload();
    await expect(page.getByRole('heading', { name: dictionary['employeeAccess.title'], exact: true })).toBeVisible();
    await page.getByTestId('business-employee-access').getByRole('button', { name: new RegExp(`employee states ${info.project.name}`) }).click();
    const action = page.getByRole('combobox', { name: new RegExp(`^${dictionary['employeeAccess.action']}`) });
    await action.focus(); await expect(action).toBeFocused();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBeTruthy();
    await page.screenshot({ path: info.outputPath(`employee-access-${language}.png`), fullPage: true });
    await page.getByTestId('access-prepare').getByRole('button', { name: dictionary['employeeAccess.clear'], exact: true }).click();
    await dialog(page, dictionary['taskWorkspace.discard']);
  }
  await page.evaluate(() => localStorage.setItem('ai_smb_language', 'ru')); await page.reload();
  await page.getByRole('textbox', { name: ru['common.search'], exact: true }).fill('no-such-employee');
  await page.getByTestId('business-employee-access').getByRole('button', { name: ru['common.search'], exact: true }).click();
  await expect(page.getByText(ru['employeeAccess.empty'], { exact: true })).toBeVisible();
  await page.route('**/employee-access/**', route => route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ code: 'temporary_service_failure', category: 'temporary' }) }));
  await page.goto(root); await expect(page.getByTestId('business-employee-access')).toHaveCount(0);
  await page.unroute('**/employee-access/**');
  await page.getByRole('button', { name: ru['platform.merchantDetail.refresh'], exact: true }).click();
  await expect(page.getByTestId('business-employee-access')).toBeVisible();
  await page.route('**/employee-access/**', route => route.fulfill({ status: 403, contentType: 'application/json', body: JSON.stringify({ code: 'permission_denied', category: 'permission' }) }));
  await page.reload(); await expect(page.getByTestId('business-employee-access')).toHaveCount(0);
});
