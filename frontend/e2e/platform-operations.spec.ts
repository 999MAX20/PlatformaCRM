import { expect, test, type Page } from '@playwright/test';
import { ru } from '../src/lib/i18n/ru';
import { kk } from '../src/lib/i18n/kk';
import { en } from '../src/lib/i18n/en';

test.beforeEach(() => test.skip(process.env.E2E_PLATFORM_OPERATIONS !== '1', 'Use the isolated Operations runner'));
async function login(page: Page) {
  await page.goto('/login');
  await page.locator('form input[type=email]').fill('platform_admin@example.com');
  await page.locator('form input[type=password]').fill(process.env.E2E_PASSWORD || 'ZaniTest123!');
  await page.locator('form button[type=submit]').click();
  await expect(page).toHaveURL(/\/platform/);
}
async function select(page: Page, name: string, option: string) {
  await page.getByRole('combobox', {name,exact:true}).click();
  await page.getByRole('option', {name:option,exact:true}).click();
}
async function noOverflow(page: Page) { expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy(); }

test('operator worklists paginate filter and retain clinic and incident return context', async ({page},info) => {
  test.setTimeout(90_000);
  await login(page);
  const prefix=`Operations ${info.project.name}`;
  await page.goto(`/platform/operations?search=${encodeURIComponent(prefix)}&page_size=10`);
  await expect(page.getByTestId('operations-count')).toContainText('24');
  await expect(page.getByTestId('operations-row')).toHaveCount(10);
  await page.getByRole('button',{name:ru['pagination.next'],exact:true}).click();
  await expect(page).toHaveURL(/page=2/);
  await page.getByTestId('operations-row').first().getByRole('link').first().click();
  await expect(page.getByTestId('support-action-history')).toBeVisible();
  await page.locator('main a[href^="/platform/operations?"]').click();
  await expect(page).toHaveURL(/page=2/);
  await page.getByTestId('operations-row').first().getByRole('link',{name:new RegExp(ru['supportIncidents.open'])}).click();
  await expect(page.getByTestId('support-incident-page')).toBeVisible();
  await page.locator('main a[href^="/platform/operations?"]').click();
  await expect(page).toHaveURL(/page=2/);
  await page.getByRole('textbox',{name:ru['operationsWorkspace.search']}).fill(`${prefix} 00`);
  await expect(page.getByTestId('operations-row')).toHaveCount(2);
  await select(page,ru['supportIncidents.source'],ru['serviceStatus.component.files']);
  await expect(page.getByTestId('operations-row')).toHaveCount(1);
  await expect(page.getByTestId('operations-row')).toContainText(ru['platform.workspace.service.unknown']);
  await select(page,ru['operationsWorkspace.freshness'],ru['operationsWorkspace.fresh']);
  await expect(page.getByText(ru['operationsWorkspace.empty'],{exact:true})).toBeVisible();
  await select(page,ru['operationsWorkspace.freshness'],ru['operationsWorkspace.unknown']);
  await expect(page.getByTestId('operations-row')).toHaveCount(1);
  await page.getByRole('button',{name:ru['tasks.resetFilters'],exact:true}).click();
  await page.getByRole('textbox',{name:ru['operationsWorkspace.search']}).fill(prefix);
  await expect(page.getByTestId('operations-row')).toHaveCount(10);
  for(const [language,copy] of [['ru',ru],['kk',kk],['en',en]] as const) {
    await page.evaluate(value=>localStorage.setItem('ai_smb_language',value),language); await page.reload();
    await expect(page.getByTestId('operations-row')).toHaveCount(10);
    await page.getByRole('textbox',{name:copy['operationsWorkspace.search']}).focus();
    await expect(page.getByRole('textbox',{name:copy['operationsWorkspace.search']})).toBeFocused();
    await noOverflow(page);
    await page.screenshot({path:info.outputPath(`operations-${language}.png`),fullPage:true});
  }
});

test('operator worklists separate dated failures connectors and infrastructure',async({page},info)=>{
  test.setTimeout(90_000);
  await login(page);
  const prefix=`Operations ${info.project.name}`;
  await page.goto(`/platform/operations?section=connectors&search=${encodeURIComponent(prefix)}&page_size=10`);
  await expect(page.getByTestId('operations-count')).toContainText('13');
  await expect(page.getByTestId('operations-row')).toHaveCount(10);
  await page.getByRole('tab',{name:ru['operationsWorkspace.history'],exact:true}).click();
  await expect(page.getByTestId('operations-count')).toContainText('13');
  await page.getByRole('button',{name:ru['operationsWorkspace.period'],exact:true}).click();
  const dialog=page.getByRole('dialog');
  await dialog.getByRole('button',{name:new RegExp(ru['operationsWorkspace.period'])}).click();
  await dialog.getByRole('button',{name:ru['crmFilters.last7'],exact:true}).click();
  await dialog.getByRole('button',{name:ru['crmFilters.apply'],exact:true}).click();
  await expect(page).toHaveURL(/date_from=/);
  await select(page,ru['operationsWorkspace.source'],ru['operationsWorkspace.webhooks']);
  await expect(page.getByTestId('operations-row')).toHaveCount(1);
  await expect(page.getByTestId('operations-row')).toContainText('lead.created');
  await page.screenshot({path:info.outputPath('webhooks.png'),fullPage:true});
  await select(page,ru['operationsWorkspace.source'],ru['operationsWorkspace.integrations']);
  await expect(page.getByTestId('operations-row')).toHaveCount(1);
  await expect(page.getByTestId('operations-row')).toContainText('telegram');
  await page.getByRole('tab',{name:ru['operationsWorkspace.infrastructure'],exact:true}).click();
  await expect(page.getByTestId('operations-infrastructure')).toBeVisible();
  await expect(page.getByTestId('operations-table')).toHaveCount(0);
  await expect(page.getByRole('heading',{name:ru['operationsWorkspace.backups'],exact:true})).toBeVisible();
  await page.getByRole('tab',{name:ru['operationsWorkspace.infrastructure'],exact:true}).focus();
  await page.keyboard.press('Home');
  await expect(page.getByRole('tab',{name:ru['operationsWorkspace.incidents'],exact:true})).toBeFocused();
  await noOverflow(page);
});

test('operator worklists preserve filters on refresh failure and hide data on permission loss',async({page},info)=>{
  test.setTimeout(90_000);
  await login(page);
  const prefix=`Operations ${info.project.name}`;
  await page.goto(`/platform/operations?search=${encodeURIComponent(prefix)}&page_size=10`);
  await expect(page.getByTestId('operations-row')).toHaveCount(10);
  const route='**/api/platform/operations-worklist/?*';
  await page.route(route,route=>route.fulfill({status:503,json:{code:'temporary_service_failure',category:'temporary'}}));
  await page.getByRole('button',{name:ru['common.refresh'],exact:true}).click();
  await expect(page.getByText(ru['platform.operations.error'],{exact:true})).toBeVisible();
  await expect(page.getByRole('textbox',{name:ru['operationsWorkspace.search']})).toHaveValue(prefix);
  await expect(page.getByTestId('operations-row')).toHaveCount(10);
  await page.unroute(route);
  await page.getByRole('button',{name:ru['common.refresh'],exact:true}).last().click();
  await expect(page.getByText(ru['platform.operations.error'],{exact:true})).toHaveCount(0);
  await page.route(route,async route=>{const response=await route.fetch();const body=await response.json();body.count=null;body.results=[];body.unavailable_sources=['incidents'];await route.fulfill({response,json:body});});
  await page.getByRole('button',{name:ru['common.refresh'],exact:true}).click();
  await expect(page.getByTestId('operations-count')).toContainText('—');
  await expect(page.getByText(ru['platform.workspace.partial'],{exact:true})).toBeVisible();
  await page.unroute(route);
  await page.getByRole('button',{name:ru['common.refresh'],exact:true}).click();
  await expect(page.getByTestId('operations-row')).toHaveCount(10);
  await page.goto(`/platform/operations?search=${encodeURIComponent(prefix)}&page_size=10&page=99`);
  await page.getByRole('button',{name:`${ru['pagination.previous']} · 1`,exact:true}).click();
  await expect(page.getByTestId('operations-row')).toHaveCount(10);
  await page.route(route,route=>route.fulfill({status:403,json:{code:'permission_denied',category:'permission'}}));
  await page.getByRole('button',{name:ru['common.refresh'],exact:true}).click();
  await expect(page.getByTestId('permission-fallback')).toBeVisible();
  await expect(page.getByTestId('operations-row')).toHaveCount(0);
});
