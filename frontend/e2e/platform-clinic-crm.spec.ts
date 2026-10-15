import { expect, test, type Page } from '@playwright/test';
import { ru } from '../src/lib/i18n/ru';
import { kk } from '../src/lib/i18n/kk';
import { en } from '../src/lib/i18n/en';

test.beforeEach(() => { test.setTimeout(90_000); test.skip(process.env.E2E_PLATFORM_CLINIC_CRM !== '1', 'Use the disposable --clinic-crm runner'); });
const api = process.env.E2E_API_BASE_URL || 'http://127.0.0.1:8000';
async function openClinic(page: Page, manager = false) {
  await page.goto('/login');
  await page.locator('form input[type=email]').fill(manager ? 'platform_manager@example.com' : 'platform_admin@example.com');
  await page.locator('form input[type=password]').fill(process.env.E2E_PASSWORD || 'ZaniTest123!');
  const pending = page.waitForResponse(response => response.url().endsWith('/api/auth/token/') && response.request().method() === 'POST');
  await page.locator('form button[type=submit]').click();
  const headers = { Authorization: `Bearer ${(await (await pending).json()).access}` };
  await expect(page.getByTestId('overview-attention')).toBeVisible();
  const response = await page.request.get(`${api}/api/platform/merchants/?search=CRM%20Acceptance%20Clinic`, { headers });
  expect(response.ok()).toBeTruthy();
  const id = (await response.json()).results[0].id;
  await page.goto(`/platform/merchants/${id}?section=work`);
  await expect(page.getByTestId('clinic-record-row')).toHaveCount(20);
  return { id, headers, root: `/platform/merchants/${id}` };
}
async function choose(page: Page, label: string, option: string) {
  await page.getByRole('combobox', { name: new RegExp('^' + label) }).click();
  await page.getByRole('option', { name: option, exact: true }).click();
}
async function selectKind(page: Page, kind: string) { await choose(page, ru['clinicCrm.records'], ru[`clinicCrm.kind.${kind}`]); }
const rows = (page: Page) => page.getByTestId('clinic-record-row');

test('clinic CRM search pagination archive and related navigation keep the selected clinic', async ({ page }) => {
  const { root } = await openClinic(page);
  await expect(page.getByTestId('clinic-pagination')).toContainText('24');
  await choose(page, ru['pagination.perPage'], '10');
  await expect(rows(page)).toHaveCount(10);
  await page.getByTestId('clinic-pagination').getByRole('button', { name: ru['pagination.next'] }).click();
  await expect(page).toHaveURL(/page=2/);
  const title = await rows(page).first().getByRole('link').innerText();
  await rows(page).first().getByRole('link').click();
  await expect(page.getByRole('heading', { name: new RegExp(title) })).toBeVisible();
  await page.getByRole('link', { name: ru['clinicCrm.back'], exact: true }).click();
  await expect(page).toHaveURL(/page=2/); await expect(rows(page)).toHaveCount(10);
  const search = page.getByRole('textbox', { name: ru['clinicCrm.search'], exact: true });
  await search.fill('CRM Patient');
  await expect(rows(page)).toHaveCount(1);
  await rows(page).getByRole('link').click();
  await expect(page.getByText('Patient detail note', { exact: true })).toBeVisible();
  await expect(page.getByText('Morning', { exact: true })).toBeVisible();
  for (const [section, text] of [['notes', 'CRM patient note'], ['activity', 'Client registered'], ['tags', 'Follow up']]) {
    await page.getByRole('tab', { name: ru[`clinicCrm.section.${section}`], exact: true }).click();
    await expect(page.getByText(text, { exact: true })).toBeVisible();
  }
  await page.getByRole('navigation', { name: ru['clinicCrm.related'], exact: true }).getByRole('button', { name: ru['clinicCrm.kind.tasks'], exact: true }).click();
  await expect(rows(page)).toHaveCount(1); await expect(page).toHaveURL(/client=/);
  await rows(page).getByRole('link').click();
  await expect(page.getByText('Patient call comment', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'CRM Patient', exact: true }).click();
  await expect(page.getByText('Patient detail note', { exact: true })).toBeVisible();
  expect(new URL(page.url()).pathname).toBe(root);
  await page.getByRole('link', { name: ru['clinicCrm.back'], exact: true }).click();
  await choose(page, ru['clinicCrm.archive'], ru['clinicCrm.archive.archived']);
  await expect(rows(page)).toHaveCount(1); await expect(rows(page)).toContainText('Archived patient');
  await search.fill('not present'); await expect(page.getByText(ru['clinicCrm.empty'], { exact: true })).toBeVisible();
});

test('clinic CRM manager can inspect every record type and messages without changing unread state', async ({ page }, info) => {
  const { id, headers } = await openClinic(page, true);
  for (const kind of ['leads', 'deals', 'tasks', 'appointments', 'payments']) {
    await selectKind(page, kind); await expect(rows(page)).toHaveCount(1);
    await rows(page).getByRole('link').click();
    await expect(page.getByTestId('clinic-record-detail')).toBeVisible();
    await expect(page.getByTestId('clinic-record-detail').getByRole('heading')).toHaveCount(1);
    await expect(page.getByTestId('permission-fallback')).toHaveCount(0);
    if (kind === 'payments') await page.screenshot({ path: info.outputPath('clinic-payment.png'), fullPage: true });
  }
  await selectKind(page, 'conversations'); await rows(page).getByRole('link').click();
  await expect(page.getByText('Patient message 22', { exact: true })).toBeVisible();
  await expect(page.getByText('Patient message 00', { exact: true })).toHaveCount(0);
  await page.getByTestId('clinic-pagination').getByRole('button', { name: ru['pagination.next'] }).click();
  await expect(page.getByText('Patient message 00', { exact: true })).toBeVisible();
  await page.screenshot({ path: info.outputPath('clinic-conversation.png'), fullPage: true });
  const response = await page.request.get(`${api}/api/platform/merchants/${id}/crm/conversations/`, { headers });
  expect((await response.json()).results[0].fields.unread_count).toBe(23);
  await expect(page.locator('main')).not.toContainText('DO_NOT_RENDER_CREDENTIAL');
  await page.getByRole('tab', { name: ru['clinicCrm.tab.connections'], exact: true }).click();
  await expect(rows(page)).toHaveCount(1); await rows(page).getByRole('link').click();
  await expect(page.getByRole('heading', { name: /CRM website/ })).toBeVisible();
  await selectKind(page, 'channels'); await expect(rows(page)).toHaveCount(1);
  await rows(page).getByRole('link').click(); await expect(page.getByText('Reception assistant', { exact: true })).toBeVisible();
  await page.getByRole('tab', { name: ru['clinicCrm.tab.access'], exact: true }).click();
  await expect(page.getByTestId('clinic-access-history')).toContainText('Shell manager');
  await expect(page.getByTestId('support-action-form')).toHaveCount(0);
  await expect(page.locator('main')).not.toContainText('DO_NOT_RENDER_CREDENTIAL');
  await page.screenshot({ path: info.outputPath('clinic-access.png'), fullPage: true });
});

test('clinic CRM support stays scoped and returns to clinic while drafts survive cancelled navigation', async ({ page }, info) => {
  const { root } = await openClinic(page);
  await page.getByRole('tab', { name: ru['clinicCrm.tab.support'], exact: true }).click();
  await expect(page.getByTestId('support-case-row').filter({ hasText: 'CRM clinic support' })).toHaveCount(1);
  await expect(page.getByText(ru['supportCases.clinicFilter'], { exact: true })).toHaveCount(0);
  await page.getByTestId('support-case-row').first().getByRole('link').click();
  await expect(page.getByTestId('support-case-detail')).toBeVisible();
  await page.locator(`main a[href="${root}?section=support"]`).click();
  await expect(page.getByTestId('support-list')).toBeVisible();
  await page.getByRole('button', { name: ru['supportCases.create'], exact: true }).click();
  await page.getByRole('textbox', { name: ru['supportCases.subject'], exact: true }).fill(`Clinic draft ${info.project.name}`);
  await page.getByRole('textbox', { name: ru['supportCases.description'], exact: true }).fill('Please review this record');
  await page.getByTestId('support-create-dialog').getByRole('button', { name: ru['common.cancel'], exact: true }).click();
  await page.getByRole('button', { name: ru['taskWorkspace.keepEditing'], exact: true }).click();
  await expect(page.getByRole('textbox', { name: ru['supportCases.description'], exact: true })).toHaveValue('Please review this record');
  await page.getByRole('button', { name: ru['supportCases.submit'], exact: true }).click();
  await expect(page.getByTestId('support-case-detail')).toBeVisible();
  await expect(page.getByTestId('support-case-detail')).toContainText('CRM Acceptance Clinic');
  await page.locator(`main a[href="${root}?section=support"]`).click();
  await expect(page.getByTestId('support-list')).toBeVisible();
});

test('clinic CRM transient failures preserve data and filters while denied child reads hide private detail', async ({ page }) => {
  const { root } = await openClinic(page);
  const listRoute = '**/api/platform/merchants/*/crm/clients/?*';
  const refresh = () => page.getByTestId('clinic-crm').getByRole('button', { name: ru['common.refresh'], exact: true }).first().click();
  await page.getByRole('textbox', { name: ru['clinicCrm.search'], exact: true }).fill('CRM Patient');
  await expect(rows(page)).toHaveCount(1);
  await page.route(listRoute, route => route.fulfill({ status: 503, json: { code: 'temporary_service_failure', category: 'temporary' } }));
  await refresh(); await expect(rows(page)).toHaveCount(1); await expect(page.getByTestId('inline-fallback')).toBeVisible();
  await expect(page.getByRole('textbox', { name: ru['clinicCrm.search'], exact: true })).toHaveValue('CRM Patient');
  await page.unroute(listRoute); await refresh(); await expect(page.getByTestId('inline-fallback')).toHaveCount(0);
  await rows(page).getByRole('link').click(); await expect(page.getByText('Patient detail note', { exact: true })).toBeVisible();
  await page.route('**/api/platform/merchants/*/crm/clients/*/notes/?*', route => route.fulfill({ status: 403, json: { code: 'permission_denied', category: 'permission' } }));
  await page.getByRole('tab', { name: ru['clinicCrm.section.notes'], exact: true }).click();
  await expect(page.getByTestId('permission-fallback')).toBeVisible();
  await expect(page.getByText('Patient detail note', { exact: true })).toHaveCount(0);
  await expect(page.getByTestId('platform-clinic-detail')).toHaveCount(0);
  await expect(page.getByRole('heading', { name: 'CRM Acceptance Clinic', exact: true })).toHaveCount(0);
  await page.goto(`${root}?section=work&entity=clients&record=999999999`);
  await expect(page.getByTestId('inline-fallback')).toBeVisible();
  await page.getByRole('link', { name: ru['clinicCrm.back'], exact: true }).click();
  await expect(rows(page)).toHaveCount(20);
  await page.route(listRoute, route => route.fulfill({ status: 403, json: { code: 'permission_denied', category: 'permission' } }));
  await refresh(); await expect(page.getByTestId('permission-fallback')).toBeVisible(); await expect(rows(page)).toHaveCount(0);
  await expect(page.getByTestId('platform-clinic-detail')).toHaveCount(0);
});

test('clinic CRM locales keyboard tabs and layout remain usable', async ({ page }, info) => {
  const { root } = await openClinic(page);
  for (const [language, copy] of [['ru', ru], ['kk', kk], ['en', en]] as const) {
    await page.evaluate(value => localStorage.setItem('ai_smb_language', value), language);
    await page.goto(`${root}?section=work`); await expect(rows(page)).toHaveCount(20);
    await expect(page.getByRole('heading', { level: 1, name: 'CRM Acceptance Clinic', exact: true })).toBeVisible();
    const work = page.getByRole('tab', { name: copy['clinicCrm.tab.work'], exact: true });
    await work.focus(); await page.keyboard.press('ArrowRight');
    await expect(page.getByRole('tab', { name: copy['clinicCrm.tab.connections'], exact: true })).toHaveAttribute('aria-selected', 'true');
    await page.keyboard.press('ArrowLeft'); await expect(work).toHaveAttribute('aria-selected', 'true');
    await expect(rows(page)).toHaveCount(20);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBeTruthy();
    await expect(page.locator('main')).not.toContainText('clinicCrm.');
    await page.screenshot({ path: info.outputPath(`clinic-${language}.png`), fullPage: true });
  }
});
