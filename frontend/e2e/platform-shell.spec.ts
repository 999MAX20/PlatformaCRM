import { expect, test, type Page } from '@playwright/test';
import { ru } from '../src/lib/i18n/ru';
import { kk } from '../src/lib/i18n/kk';
import { en } from '../src/lib/i18n/en';

test.beforeEach(() => test.skip(process.env.E2E_PLATFORM_OVERVIEW !== '1', 'Use isolated overview fixtures'));
test.use({ actionTimeout: 10_000 });
test.afterEach(async ({ request }, info) => {
  if (process.env.E2E_PLATFORM_OVERVIEW !== '1' || !info.title.includes('self account')) return;
  const response = await request.post('/api/auth/token/', { data: { email: 'platform_manager@example.com', password: process.env.E2E_PASSWORD || 'ZaniTest123!' } });
  expect(response.ok()).toBeTruthy();
  const { access } = await response.json();
  const reset = await request.patch('/api/auth/me/', { headers: { Authorization: `Bearer ${access}` }, data: { full_name: 'Shell manager', preferences: { language: 'ru' } } });
  expect(reset.ok()).toBeTruthy();
});
async function login(page: Page, email = 'platform_admin@example.com') {
  await page.goto('/login');
  await page.locator('form input[type=email]').fill(email);
  await page.locator('form input[type=password]').fill(process.env.E2E_PASSWORD || 'ZaniTest123!');
  await page.locator('form button[type=submit]').click();
  await expect(page.getByTestId('overview-attention')).toBeVisible();
}
const menu = (page: Page) => page.locator('header button[aria-haspopup=menu]');

test('platform shell route titles, overlay navigation, keyboard menu and history', async ({ page }, info) => {
  test.setTimeout(90_000);
  await login(page);
  for (const [language, copy] of [['ru', ru], ['kk', kk], ['en', en]] as const) {
    await page.evaluate(value => localStorage.setItem('ai_smb_language', value), language);
    await page.goto('/platform');
    await expect(page.getByTestId('overview-attention')).toBeVisible();
    for (const [path, key, ready] of [
      ['/platform', 'platform.nav.overview', 'platform-overview-ready'],
      ['/platform/merchants', 'platform.nav.merchants', 'platform-merchants-ready'],
      ['/platform/support', 'supportCases.title', 'support-list'],
      ['/platform/operations', 'platform.nav.operations', 'platform-operations-ready'],
    ]) {
      await page.goto(path); await expect(page.getByTestId(ready)).toBeVisible();
      await expect(page.locator('h1')).toHaveText(copy[key]);
      expect(await page.locator('header').evaluate(el => el.getBoundingClientRect().height)).toBe(57);
      const inset = await page.locator('main').evaluate(el => parseFloat(getComputedStyle(el).paddingTop));
      expect(inset).toBe(info.project.name === 'mobile-chromium' ? 16 : 24);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBeTruthy();
    }
    await page.screenshot({ path: info.outputPath(`shell-${language}.png`), fullPage: true });
  }
  if (info.project.name === 'desktop-chromium') {
    const sidebar = page.getByTestId('platform-sidebar');
    const mainLeft = await page.locator('main').evaluate(el => el.getBoundingClientRect().left);
    await sidebar.hover();
    await expect.poll(() => sidebar.evaluate(el => el.getBoundingClientRect().width)).toBe(224);
    expect(await page.locator('main').evaluate(el => el.getBoundingClientRect().left)).toBe(mainLeft);
    await sidebar.locator('a[href="/platform/merchants"]').click();
    await menu(page).hover();
    await expect.poll(() => sidebar.evaluate(el => el.getBoundingClientRect().width)).toBe(64);
    await menu(page).focus(); await page.keyboard.press('Shift+Tab');
    await expect.poll(() => sidebar.evaluate(el => el.getBoundingClientRect().width)).toBe(224);
    await menu(page).focus();
    await expect.poll(() => sidebar.evaluate(el => el.getBoundingClientRect().width)).toBe(64);
  }
  await menu(page).focus(); await page.keyboard.press('Enter');
  await expect(page.getByRole('menuitem').first()).toBeFocused();
  await page.keyboard.press('End'); await expect(page.getByRole('menuitem').last()).toBeFocused();
  await page.keyboard.press('Home'); await page.keyboard.press('ArrowDown');
  await expect(page.getByRole('menuitem').nth(1)).toBeFocused();
  await page.keyboard.press('Escape'); await expect(menu(page)).toBeFocused();
  await menu(page).click(); await page.getByRole('menuitem').nth(1).click();
  await expect(page).toHaveURL(/\/platform\/account#security$/);
  await expect(page.locator('h1')).toHaveText(ru['platform.shell.account']); // saved account language
  await expect(page.locator('#security')).toBeInViewport();
  await page.goBack(); await expect(page).not.toHaveURL(/account/);
  await page.goForward(); await expect(page.locator('[data-account-page]')).toBeVisible();
});

test('platform shell clears entity metadata on navigation, failure and access denial', async ({ page }) => {
  await login(page);
  await page.getByTestId('overview-clinic-row').first().getByRole('link').first().click();
  await expect(page.locator('h1')).toContainText('Overview Clinic');
  const clinicUrl = page.url();
  await page.locator('main a[href="/platform"]').click();
  await expect(page.locator('h1')).toHaveText(ru['platform.nav.overview']);
  await page.getByTestId('overview-case-row').first().getByRole('link').click();
  await expect(page.locator('h1')).toContainText(ru['platform.shell.case']);
  await expect(page.locator('h1')).toHaveCount(1);
  await page.locator('main a[href="/platform"]').click();
  const row = page.getByTestId('overview-clinic-row').first();
  await row.locator('summary').click();
  await row.getByRole('link', { name: new RegExp(ru['supportIncidents.open']) }).click();
  await expect(page.locator('h1')).toHaveText(ru['supportIncidents.open']);
  for (const status of [503, 403]) {
    await page.route('**/api/platform/merchants/*/', route => route.fulfill({ status, json: { detail: 'Unavailable', code: status === 403 ? 'permission_denied' : 'temporary_service_failure' } }));
    await page.goto(clinicUrl);
    await expect(page.locator('h1')).toHaveText(ru['supportCases.clinic']);
    await expect(page.getByTestId('platform-clinic-detail')).toHaveCount(0);
    await page.unroute('**/api/platform/merchants/*/');
  }
  await page.reload(); await expect(page.locator('h1')).toContainText('Overview Clinic');
  // Use the supported explicit refresh to deny an already mounted entity.
  await page.goto('/platform/support');
  await page.getByTestId('support-case-row').first().getByRole('link').click();
  await expect(page.locator('h1')).toContainText(ru['platform.shell.case']);
  await page.route(/\/api\/platform\/support-cases\/\d+\/$/, route => route.fulfill({ status: 403, json: { code: 'permission_denied' } }));
  await page.getByRole('button', { name: ru['common.refresh'], exact: true }).click();
  await expect(page.getByTestId('permission-fallback')).toBeVisible();
  await expect(page.locator('h1')).toHaveText(ru['platform.shell.case']);
});

test('platform shell bounds long identity and clinic titles and preserves merchant support', async ({ page }) => {
  await page.route('**/api/auth/me/', async route => {
    const response = await route.fetch(); const user = await response.json();
    user.email = `${'long.identity.'.repeat(14)}@example.com`;
    await route.fulfill({ response, json: user });
  });
  await login(page);
  await page.route('**/api/platform/merchants/*/', async route => {
    const response = await route.fetch(); const item = await response.json();
    item.name = 'Длинное название клиники '.repeat(15);
    await route.fulfill({ response, json: item });
  });
  await page.getByTestId('overview-clinic-row').first().getByRole('link').first().click();
  await expect(page.locator('h1')).toContainText('Длинное название');
  expect(await page.locator('header').evaluate(el => el.getBoundingClientRect().height)).toBe(57);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBeTruthy();
  await menu(page).click(); await page.locator('main').click({ position: { x: 5, y: 5 } });
  await expect(page.getByRole('menu')).toHaveCount(0);
  await expect(menu(page)).toBeFocused();
  await menu(page).click(); await page.getByRole('menuitem').last().click();
  await expect(page).toHaveURL(/login/);
  await page.unroute('**/api/auth/me/');
  await page.locator('form input[type=email]').fill('business_owner@example.com');
  await page.locator('form input[type=password]').fill(process.env.E2E_PASSWORD || 'ZaniTest123!');
  const ownerLogin = page.waitForResponse(response => response.url().endsWith('/api/auth/token/') && response.request().method() === 'POST');
  await page.locator('form button[type=submit]').click();
  const { access } = await (await ownerLogin).json();
  const headers = { Authorization: `Bearer ${access}` };
  const current = await page.request.get('/api/auth/me/', { headers });
  const owner = await current.json();
  const task = await page.request.post('/api/tasks/', { headers, data: { title: 'Shell menu regression', business: owner.businesses[0].id, assignee: owner.id } });
  expect(task.status()).toBe(201);
  await expect(page.getByTestId('header-account-link')).toBeVisible();
  await page.goto('/platform/account'); await expect(page).toHaveURL(/\/app/);
  await page.goto('/app/support'); await expect(page.getByTestId('support-list')).toBeVisible();
  await page.getByRole('button', { name: ru['supportCases.create'], exact: true }).click();
  await expect(page.getByTestId('support-create-dialog')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByTestId('support-create-dialog')).toHaveCount(0);
  await page.goto('/app/tasks');
  await page.getByTestId('task-row').first().click();
  const actions = page.getByTestId('task-inspector').getByTestId('row-actions-trigger');
  await actions.click(); await expect(page.getByRole('menuitem').first()).toBeFocused();
  await page.keyboard.press('End'); await expect(page.getByRole('menuitem').last()).toBeFocused();
  await page.keyboard.press('Escape'); await expect(actions).toBeFocused();
});

test('platform shell self account saves without Business requests, preserves drafts and logs out', async ({ page }, info) => {
  test.setTimeout(90_000);
  await login(page, 'platform_manager@example.com');
  const requests: string[] = [];
  page.on('request', request => { if (request.url().includes('/api/')) requests.push(request.url()); });
  await menu(page).click(); await page.getByRole('menuitem').first().click();
  await expect(page.locator('[data-account-page]')).toBeVisible();
  await expect(page.locator('h1')).toHaveCount(1);
  await expect(page.locator('#notifications')).toHaveCount(0);
  await expect(page.locator('#interface').getByRole('combobox')).toHaveCount(1);
  const name = page.locator('#profile input[autocomplete=name]');
  const original = await name.inputValue();
  await name.fill(`Shell manager ${info.project.name}`);
  await page.route('**/api/auth/me/', route => route.request().method() === 'PATCH' ? route.fulfill({ status: 503, json: { detail: 'Temporarily unavailable' } }) : route.continue());
  await page.locator('#profile button[type=submit]').click();
  await expect(page.locator('#profile').getByRole('alert')).toBeVisible();
  await expect(name).toHaveValue(`Shell manager ${info.project.name}`);
  await page.unroute('**/api/auth/me/');
  await page.locator('#profile button[type=submit]').click();
  await expect(page.locator('#profile [role=status]')).toHaveText(ru['account.saved']);
  await name.fill('Preserved draft');
  const settings = page.locator('#interface');
  await settings.getByRole('combobox').click(); await page.getByRole('option', { name: 'English', exact: true }).click();
  const saved = page.waitForResponse(response => response.url().endsWith('/api/auth/me/') && response.request().method() === 'PATCH');
  await settings.locator('button[type=submit]').click();
  expect((await saved).request().postDataJSON()).toEqual({ preferences: { language: 'en' } });
  await expect(page.locator('h1')).toHaveText(en['platform.shell.account']);
  await expect(name).toHaveValue('Preserved draft');
  await page.reload(); await expect(page.locator('h1')).toHaveText(en['platform.shell.account']);
  await page.getByRole('button', { name: en['account.changePassword'], exact: true }).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel(en['account.currentPassword'], { exact: true }).fill('wrong-password');
  await dialog.getByLabel(en['account.newPassword'], { exact: true }).fill('AnotherTest123!');
  await dialog.getByLabel(en['account.confirmPassword'], { exact: true }).fill('AnotherTest123!');
  await dialog.getByRole('button', { name: en['account.changePassword'], exact: true }).click();
  await expect(dialog.getByRole('alert')).toBeVisible();
  await expect(dialog.getByLabel(en['account.currentPassword'], { exact: true })).toHaveValue('wrong-password');
  await page.keyboard.press('Escape');
  await name.fill(original); await page.locator('#profile button[type=submit]').click();
  await expect(page.locator('#profile button[type=submit]')).toBeDisabled();
  await settings.getByRole('combobox').click(); await page.getByRole('option', { name: 'Русский', exact: true }).click();
  await settings.locator('button[type=submit]').click(); await expect(page.locator('h1')).toHaveText(ru['platform.shell.account']);
  expect(requests.filter(url => /\/api\/(businesses|notifications|notification-preferences)\//.test(url))).toEqual([]);
  await page.evaluate(() => window.scrollTo(0, 0));
  const sectionNav = await page.locator('.account-section-nav-rail nav').boundingBox();
  expect(sectionNav!.x).toBeGreaterThanOrEqual(info.project.name === 'desktop-chromium' ? 64 : 0);
  await page.screenshot({ path: info.outputPath('platform-account.png'), fullPage: true });
  await menu(page).click(); await page.getByRole('menuitem').last().click();
  await expect(page).toHaveURL(/\/login/);
  await page.goto('/platform/account'); await expect(page).toHaveURL(/\/login/);
});
