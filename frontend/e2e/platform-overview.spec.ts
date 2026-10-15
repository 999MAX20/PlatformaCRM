import { expect, test, type Page } from '@playwright/test';
import { ru } from '../src/lib/i18n/ru';
import { kk } from '../src/lib/i18n/kk';
import { en } from '../src/lib/i18n/en';

test.beforeEach(()=>test.skip(process.env.E2E_PLATFORM_OVERVIEW!=='1','Use the isolated overview runner'));
async function login(page:Page) {
  await page.goto('/login');
  await page.locator('form input[type=email]').fill('platform_admin@example.com');
  await page.locator('form input[type=password]').fill(process.env.E2E_PASSWORD || 'ZaniTest123!');
  await page.locator('form button[type=submit]').click();
  await expect(page.getByTestId('overview-attention')).toBeVisible();
}
async function home(page:Page) { await page.goto('/platform');await expect(page.getByTestId('overview-attention')).toBeVisible(); }
const overviewLink=(page:Page)=>page.locator('main a[href="/platform"]').filter({hasText:ru['platform.nav.overview']});

test('operator overview metrics reach exactly filtered clinic and support lists',async({page})=>{
  await login(page);
  await page.getByRole('link',{name:ru['overviewWorkspace.degradedClinics'],exact:true}).click();
  await expect(page).toHaveURL(/service=degraded/);
  await expect(page.getByTestId('platform-clinic-row')).toHaveCount(9);
  const input=page.getByRole('textbox',{name:ru['platform.merchants.search']});
  await input.fill('Overview Clinic 00');
  await expect(page.getByTestId('platform-clinic-row')).toHaveCount(1);
  await page.getByTestId('platform-clinic-row').getByRole('link').click();
  await page.locator('main a[href^="/platform/merchants?"]').click();
  await expect(page).toHaveURL(/service=degraded/);
  await expect(input).toHaveValue('Overview Clinic 00');
  await home(page);
  await page.getByRole('link',{name:ru['overviewWorkspace.unknownClinics'],exact:true}).click();
  await expect(page.getByTestId('platform-clinic-row')).toHaveCount(3);
  await home(page);
  await page.getByRole('link',{name:ru['overviewWorkspace.unassignedCases'],exact:true}).click();
  await expect(page).toHaveURL(/status=active&assignee=unassigned/);
  await expect(page.getByTestId('support-case-row')).toHaveCount(9);
  await home(page);
  await page.getByRole('link',{name:ru['supportCases.status.waiting_clinic'],exact:true}).click();
  await expect(page.getByTestId('support-case-row')).toHaveCount(9);
  await home(page);
  await page.getByRole('link',{name:ru['overviewWorkspace.activeCases'],exact:true}).click();
  await expect(page.getByTestId('support-case-row')).toHaveCount(18);
});

test('operator overview bounded queues return from clinic incident and case across locales',async({page},info)=>{
  test.setTimeout(90_000);
  await login(page);
  await expect(page.getByTestId('overview-clinic-row')).toHaveCount(6);
  await expect(page.getByTestId('overview-case-row')).toHaveCount(6);
  await expect(page.getByTestId('overview-clinics')).toContainText('6 из 12');
  await expect(page.getByTestId('overview-support')).toContainText('6 из 18');
  await page.getByTestId('overview-clinic-row').first().getByRole('link').first().click();
  await expect(page.getByTestId('platform-clinic-detail')).toBeVisible();
  await overviewLink(page).click();
  const first=page.getByTestId('overview-clinic-row').first();
  await first.locator('summary').focus(); await page.keyboard.press('Enter');
  await first.getByRole('link',{name:new RegExp(ru['supportIncidents.open'])}).click();
  await expect(page.getByTestId('support-incident-page')).toBeVisible();
  await overviewLink(page).click();
  await page.getByTestId('overview-case-row').first().getByRole('link').click();
  await expect(page.getByTestId('support-case-detail')).toBeVisible();
  await overviewLink(page).click();
  for(const [language,copy] of [['ru',ru],['kk',kk],['en',en]] as const) {
    await page.evaluate(value=>localStorage.setItem('ai_smb_language',value),language);await page.reload();
    await expect(page.getByTestId('overview-attention')).toBeVisible();
    await expect(page.getByTestId('platform-finance')).toBeVisible();
    const link=page.getByRole('link',{name:copy['overviewWorkspace.degradedClinics'],exact:true});
    await link.focus();await expect(link).toBeFocused();
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();
    await page.screenshot({path:info.outputPath(`overview-${language}.png`),fullPage:true});
  }
});

test('operator overview preserves last snapshot on failure and distinguishes partial empty and forbidden',async({page})=>{
  await login(page);
  const route='**/api/platform/overview/';
  const refresh=()=>page.getByRole('button',{name:ru['platform.merchantDetail.refresh'],exact:true}).last().click();
  await page.route(route,r=>r.fulfill({status:503,json:{code:'temporary_service_failure',category:'temporary'}}));
  await refresh();
  await expect(page.getByText(ru['platform.overview.error'],{exact:true})).toBeVisible();
  await expect(page.getByTestId('overview-case-row')).toHaveCount(6);
  await page.unroute(route);await refresh();
  await expect(page.getByText(ru['platform.overview.error'],{exact:true})).toHaveCount(0);
  await page.route(route,async r=>{const response=await r.fetch();const body=await response.json();body.attention.support=null;body.attention.unavailable_sources=['support'];await r.fulfill({response,json:body});});
  await refresh();
  await expect(page.getByTestId('overview-support').getByText(ru['platform.workspace.unknown'],{exact:true})).toBeVisible();
  await expect(page.getByTestId('overview-clinic-row')).toHaveCount(6);
  await page.unroute(route);
  await page.route(route,async r=>{const response=await r.fetch();const body=await response.json();body.attention.clinics={count:0,degraded:0,unknown:0,links_available:true,results:[]};body.attention.support={count:0,unassigned:0,waiting_clinic:0,results:[]};await r.fulfill({response,json:body});});
  await refresh();
  await expect(page.getByText(ru['overviewWorkspace.noClinicAttention'],{exact:true})).toBeVisible();
  await expect(page.getByText(ru['overviewWorkspace.noOpenCases'],{exact:true})).toBeVisible();
  await page.unroute(route);await refresh();
  await expect(page.getByTestId('overview-case-row')).toHaveCount(6);
  await page.route(route,r=>r.fulfill({status:403,json:{code:'permission_denied',category:'permission'}}));
  await refresh();
  await expect(page.getByTestId('permission-fallback')).toBeVisible();
  await expect(page.getByTestId('overview-attention')).toHaveCount(0);
});
