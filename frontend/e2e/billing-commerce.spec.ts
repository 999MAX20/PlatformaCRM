import { createHmac } from 'node:crypto';
import { expect, test, type Page } from '@playwright/test';
import { ru } from '../src/lib/i18n/ru';
import { kk } from '../src/lib/i18n/kk';
import { en } from '../src/lib/i18n/en';

test.beforeEach(() => { test.setTimeout(150_000); test.skip(process.env.E2E_BILLING_COMMERCE !== '1', 'Use verify_billing_commerce.py'); });
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
  await page.locator('form input[type=email]').fill(`billing-${scenario}-${kind}-${project}@example.com`);
  await page.locator('form input[type=password]').fill(process.env.E2E_PASSWORD || 'ZaniTest123!');
  const response = page.waitForResponse(r => r.url().endsWith('/api/auth/token/') && r.request().method() === 'POST');
  await page.locator('form button[type=submit]').click(); const result = await response;
  expect(result.ok()).toBeTruthy(); await expect(page).not.toHaveURL(/\/login/);
  return { Authorization: `Bearer ${(await result.json()).access}` };
}
async function pick(page: Page, label: string, option: string) {
  await page.getByRole('combobox', { name: new RegExp(`^${label}`) }).click();
  await page.getByRole('option', { name: option, exact: true }).click();
}
async function create(page: Page) {
  await page.goto('/app/settings#billing');
  await expect(page.getByTestId('billing-create')).toBeVisible();
  const offer=page.getByRole('combobox', { name: new RegExp(`^${ru['commerce.offer']}`) });
  await offer.focus();await offer.press('ArrowDown');await offer.press('Enter');
  await expect(offer).toContainText('12000');
  await page.locator('[name=buyer_name]').fill('TEST buyer');
  await page.getByTestId('billing-create').locator('[name=tax_id]').fill('000000000001');
  await page.locator('[name=buyer_email]').fill('test@example.com');
  const response=page.waitForResponse(r => /\/orders\/$/.test(r.url()) && r.request().method() === 'POST');
  await page.getByRole('button', { name: ru['commerce.create'], exact: true }).click();
  const result=await response; expect(result.status()).toBe(200);
  const id=(await result.json()).id as string;
  await expect(page.locator(`[data-order-id="${id}"]`)).toBeVisible(); return id;
}
async function operator(page: Page, project: string, scenario: string) {
  const headers=await login(page,project,scenario,'operator');
  const businesses=await page.request.get(`${api}/api/platform/merchants/?search=${encodeURIComponent(`Billing ${scenario} ${project}`)}`,{headers});
  const id=(await businesses.json()).results.find((row: {name:string})=>row.name===`Billing ${scenario} ${project}`).id;
  const cases=await page.request.get(`${api}/api/platform/support-cases/?business=${id}`,{headers});const caseId=(await cases.json()).results[0].id;
  await page.goto('about:blank');
  const start=await page.request.post(`${api}/api/auth/mfa/enrollment/start/`,{headers,data:{}});const enrollment=await start.json();
  const confirmed=await page.request.post(`${api}/api/auth/mfa/enrollment/confirm/`,{data:{challenge_token:enrollment.challenge_token,code:totp(enrollment.manual_key)}});
  expect(confirmed.ok()).toBeTruthy();const codes:string[]=(await confirmed.json()).recovery_codes;
  await page.goto(`/platform/merchants/${id}?section=billing`);
  await expect(page.getByTestId('platform-billing')).toBeVisible();return {id,caseId,codes};
}
async function command(page: Page, caseId: number, code: string, action: string) {
  await page.getByRole('button',{name:ru['commerce.selectOrder'],exact:true}).first().click();
  await pick(page,ru['commerce.action'],ru[`commerce.action.${action}`]);
  const form=page.getByTestId('billing-action');
  await form.locator('[name=support_case_id]').fill(String(caseId));
  await form.getByRole('textbox',{name:ru['supportCases.reason'],exact:true}).fill('TEST payment verification');
  await form.locator('[name=mfa]').fill(code);
  return form;
}
async function submit(page: Page, action: string) {
  const label=ru[`commerce.action.${action}`];
  await page.getByTestId('billing-action').getByRole('button',{name:label,exact:true}).click();
  const response=page.waitForResponse(r=>r.url().includes(`/${action}/`) && r.request().method()==='POST');
  await page.getByRole('dialog').getByRole('button',{name:label,exact:true}).click();
  const result=await response;expect(result.status()).toBe(200);return result.json();
}

test('bank order confirmation and merchant result',async({page,browser},info)=>{
  await login(page,info.project.name,'bank','owner');const order=await create(page);
  const row=page.locator(`[data-order-id="${order}"]`);
  await row.getByText(ru['commerce.bankDetails'],{exact:true}).click();await expect(row).toContainText('TEST-NOT-AN-ACCOUNT');
  const context=await browser.newContext({baseURL:new URL(page.url()).origin,viewport:page.viewportSize()!});
  try {
    const op=await context.newPage();const {caseId,codes}=await operator(op,info.project.name,'bank');
    const form=await command(op,caseId,codes[0],'confirm-bank');
    await form.locator('[name=bank_reference]').fill(`bank-ui-${info.project.name}`);
    await form.locator('[name=received_at]').fill(new Date(Date.now()-60_000).toISOString().slice(0,16));
    const result=await submit(op,'confirm-bank');expect(result.application_status).toBe('applied');
    await page.getByTestId('merchant-billing').getByRole('button',{name:ru['common.refresh'],exact:true}).click();
    await expect(row).toContainText(ru['commerce.state.applied']);
    await op.screenshot({path:info.outputPath('bank-confirmed.png'),fullPage:true});
  } finally {await context.close();}
});

test('card checkout and verified reconciliation',async({page},info)=>{
  await login(page,info.project.name,'card','owner');const order=await create(page);const row=page.locator(`[data-order-id="${order}"]`);
  await row.getByRole('button',{name:ru['commerce.payCard'],exact:true}).click();
  await expect(row.getByRole('link',{name:ru['commerce.openCheckout'],exact:true})).toHaveAttribute('href',/^https:\/\/payments\.example\.com\/pay\//);
  await row.getByRole('button',{name:ru['commerce.checkPayment'],exact:true}).click();
  await expect(row).toContainText(ru['commerce.state.applied']);
  await row.getByRole('button',{name:ru['commerce.checkPayment'],exact:true}).click();
  await expect(row).toContainText(ru['commerce.state.applied']);
  await page.screenshot({path:info.outputPath('card-applied.png'),fullPage:true});
});

test('recovery preserves one application',async({page},info)=>{
  const {caseId,codes}=await operator(page,info.project.name,'recovery');
  await expect(page.getByTestId('platform-billing')).toContainText(ru['commerce.code.temporary_failure']);
  await command(page,caseId,codes[0],'recover');let result=await submit(page,'recover');expect(result.application_status).toBe('applied');
  await command(page,caseId,codes[1],'recover');result=await submit(page,'recover');
  expect(result.events.filter((row:{kind:string})=>row.kind==='application_completed')).toHaveLength(1);
  await page.screenshot({path:info.outputPath('recovery-applied.png'),fullPage:true});
});

test('billing empty locale errors and permission states',async({page},info)=>{
  await operator(page,info.project.name,'states');
  for(const [language,dictionary] of [['ru',ru],['kk',kk],['en',en]] as const){
    await page.evaluate(lang=>localStorage.setItem('ai_smb_language',lang),language);await page.reload();
    await expect(page.getByTestId('platform-billing')).toContainText(dictionary['commerce.empty']);
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+2)).toBeTruthy();
    await page.screenshot({path:info.outputPath(`billing-${language}.png`),fullPage:true});
  }
  await page.route('**/billing-orders/**',route=>route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({code:'temporary_service_failure',category:'temporary'})}));
  await page.reload();await expect(page.getByTestId('inline-fallback')).toBeVisible();await expect(page.getByTestId('platform-billing')).toHaveCount(0);
  await page.unroute('**/billing-orders/**');await page.reload();await expect(page.getByTestId('platform-billing')).toBeVisible();
  await page.route('**/billing-orders/**',route=>route.fulfill({status:403,contentType:'application/json',body:JSON.stringify({code:'permission_denied',category:'permission'})}));
  await page.reload();await expect(page.getByTestId('inline-fallback')).toBeVisible();await expect(page.getByTestId('platform-billing')).toHaveCount(0);
});
