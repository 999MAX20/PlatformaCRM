const { test, expect } = require('@playwright/test');
const fs = require('fs');
const output = process.env.IMPORT_WORKSPACE_OUTPUT;
if (!output) throw new Error('Run through scripts/verify_import_workspace.py');
const fixture = JSON.parse(fs.readFileSync(`${output}/ui-fixture.json`));
const dictionaries = Object.fromEntries(['en','ru','kk'].map(lang => [lang, require(`../src/lib/i18n/${lang}/importWorkspace.ts`).importWorkspace]));
const text = (key, lang='en') => dictionaries[lang][`importWorkspace.${key}`];
async function login(page, lang='en', email='business_owner@example.com') {
  await page.addInitScript(lang => localStorage.setItem('ai_smb_language', lang),lang);
  await page.route('**/api/auth/me/',async route => {const response=await route.fetch();const user=await response.json();await route.fulfill({response,json:{...user,preferences:{...user.preferences,language:lang}}});});
  await page.goto('/login');
  await page.locator('input[type=email]').fill(email);await page.locator('input[type=password]').fill(process.env.E2E_PASSWORD);
  const tokenResponse = page.waitForResponse(response => response.url().endsWith('/api/auth/token/') && response.request().method()==='POST');
  await page.locator('form button[type=submit]').click();
  const token=(await (await tokenResponse).json()).access;
  await expect(page).toHaveURL(/\/app/);
  await page.goto('/app/integrations/import');
  page.importToken = token;
  return token;
}
async function emptyDraft(page) {
 const draft=await post(page,page.importToken,'import-workspaces/',{business:fixture.business});
 await page.goto(`/app/integrations/import?draft=${draft.id}`);
}
async function choose(page, locator, label) { await locator.click();await page.getByRole('option',{name:label,exact:true}).click(); }
async function post(page, token, path, data) {
 const response=await page.request.post(`${process.env.E2E_API_BASE_URL}/api/${path}`,{headers:{Authorization:`Bearer ${token}`},data});
 expect(response.ok(),await response.text()).toBeTruthy();return response.json();
}
async function addSource(page, kind, filename, csv) {
 await choose(page,page.getByRole('combobox',{name:new RegExp('^'+text('entity')+' ')}).first(),text(kind));
 const chooser=page.waitForEvent('filechooser');await page.getByRole('button',{name:text('upload'),exact:true}).click();await chooser;
 const uploaded=page.waitForResponse(r=>r.url().endsWith('/upload/')&&r.request().method()==='POST');
 await page.locator('input[type=file]').setInputFiles({name:filename,mimeType:'text/csv',buffer:Buffer.from(csv)});
 const response=await uploaded;expect(response.ok(),await response.text()).toBeTruthy();
 await page.getByRole('navigation',{name:text('sources')}).getByRole('button').filter({hasText:filename}).click();
 await page.getByRole('button',{name:text('suggestions'),exact:true}).click();
 return response.json();
}
async function save(page) { const saved=page.waitForResponse(r=>r.url().endsWith('/save_source/')&&r.request().method()==='POST');await page.getByRole('button',{name:text('save'),exact:true}).click();const response=await saved;expect(response.ok(),await response.text()).toBeTruthy();return response.json(); }

test('four files, custom field, correction, preview, confirm and real consumers',async({page})=>{
 await page.setViewportSize({width:1440,height:1000});const errors=[];page.on('pageerror',error=>errors.push(error.message));
 const token=await login(page);
 await expect(page.getByRole('heading',{name:text('title'),exact:true})).toBeVisible();
 await emptyDraft(page);
 await expect(page).toHaveURL(/draft=\d+/);
 const id=Number(new URL(page.url()).searchParams.get('draft'));
 await addSource(page,'clients','clients.csv','external_id,full_name,phone,category\nC100,Transfer Client,+77015551234,Silver\n');
 await choose(page,page.getByRole('combobox',{name:`category: ${text('targetField')}`,exact:true}),text('custom'));
 await page.getByRole('textbox',{name:text('label'),exact:true}).fill('Loyalty');
 await page.getByRole('checkbox',{name:text('in_filters'),exact:true}).check();
 await save(page);
 await page.getByRole('button',{name:text('data'),exact:true}).click();
 await page.getByRole('button',{name:`${text('edit')}: ${text('row')} 1`,exact:true}).click();
 const editor=page.getByRole('dialog');await editor.getByRole('textbox',{name:'full_name',exact:true}).fill('Transfer Client Edited');await editor.getByRole('button',{name:text('save'),exact:true}).click();
 await expect(page.getByRole('button',{name:text('check'),exact:true})).toBeDisabled();
 await save(page);
 await page.getByRole('button',{name:text('fields'),exact:true}).click();
 await page.getByRole('textbox',{name:text('profileName'),exact:true}).fill('Transfer clients');
 await page.getByRole('button',{name:text('saveProfile'),exact:true}).click();
 await expect(page.getByRole('textbox',{name:text('profileName'),exact:true})).toHaveValue('');
 await addSource(page,'services','services.csv','external_id,name,duration_minutes,price_from,rating\nS100,Transfer Service,30,0,4\n');
 await choose(page,page.getByRole('combobox',{name:`rating: ${text('targetField')}`,exact:true}),text('custom'));
 await page.getByRole('textbox',{name:text('label'),exact:true}).fill('Rating');await save(page);
 await addSource(page,'specialists','specialists.csv','external_id,name\nP100,Transfer Specialist\n');await save(page);
 await addSource(page,'appointments','appointments.csv','external_id,client_ref,service_ref,specialist_ref,start_at,status,room\nA100,C100,S100,P100,2026-12-14T10:00:00+05:00,confirmed,Room A\n');
 await choose(page,page.getByRole('combobox',{name:`room: ${text('targetField')}`,exact:true}),text('custom'));
 await page.getByRole('textbox',{name:text('label'),exact:true}).fill('Room');await page.getByRole('checkbox',{name:text('in_calendar'),exact:true}).check();await save(page);
 await page.getByRole('button',{name:text('check'),exact:true}).click();
 await expect(page.getByRole('button',{name:text('confirm'),exact:true}).first()).toBeEnabled({timeout:30000});
 await choose(page,page.getByRole('combobox',{name:new RegExp('^'+text('entity')+' ')}).last(),text('appointments'));
 await page.getByRole('button',{name:text('calendar'),exact:true}).click();
 await expect(page.getByTestId('calendar-board-week')).toBeVisible();
 await expect(page.getByText('Transfer Client Edited',{exact:true}).last()).toBeVisible();
 await expect(page.getByText('Room: Room A',{exact:true})).toBeVisible();
 await page.screenshot({path:`${output}/ui-calendar.png`,fullPage:true});
 await page.getByRole('button',{name:text('confirm'),exact:true}).click();
 await page.getByRole('dialog').getByRole('button',{name:text('confirm'),exact:true}).click();
 await expect(page.getByRole('button',{name:text('activateReview'),exact:true})).toBeVisible({timeout:30000});
 const response=await page.request.get(`${process.env.E2E_API_BASE_URL}/api/import-workspaces/${id}/`,{headers:{Authorization:`Bearer ${token}`}});const workspace=await response.json();
 expect(workspace.state).toBe('imported');expect(workspace.result.rows).toHaveLength(4);
 const client=workspace.result.rows.find(row=>row.entity_type==='clients');const service=workspace.result.rows.find(row=>row.entity_type==='services');
 expect(client.values.full_name).toBe('Transfer Client Edited');
 const fields=await page.request.get(`${process.env.E2E_API_BASE_URL}/api/custom-field-values/context/?business=${fixture.business}&entity_type=client&ids=${client.id}`,{headers:{Authorization:`Bearer ${token}`}});
 expect((await fields.json()).values[0].value_json.value).toBe('Silver');
 await page.getByRole('button',{name:text('activateReview'),exact:true}).click();
 await expect(page.getByRole('dialog').getByText('Transfer Client Edited',{exact:false})).toBeVisible();
 await page.getByRole('dialog').getByRole('checkbox').check();await page.getByRole('dialog').getByRole('button',{name:text('activateConfirm'),exact:true}).click();
 await expect(page.getByRole('dialog').getByText(text('activated'),{exact:true})).toBeVisible();
 await page.getByRole('dialog').getByRole('button',{name:text('close'),exact:true}).last().click();
 await page.goto(`/app/clients?search=Transfer`);
 await expect(page.getByRole('columnheader',{name:'Loyalty',exact:true})).toBeVisible();await expect(page.getByRole('gridcell',{name:'Silver',exact:true})).toBeVisible();
 await choose(page,page.getByRole('combobox',{name:new RegExp('^'+text('customFilter')+' ')}),'Loyalty');
 await page.getByRole('textbox',{name:text('value'),exact:true}).fill('Silver');await page.getByRole('button',{name:text('applyFilter'),exact:true}).click();
 await expect(page.getByRole('gridcell',{name:'Silver',exact:true})).toBeVisible();
 const downloaded=page.waitForEvent('download');await page.getByRole('button',{name:text('exportAll'),exact:true}).click();
 const file=await downloaded;const csv=fs.readFileSync(await file.path(),'utf8');expect(csv).toContain('Transfer Client Edited');expect(csv).toContain('Silver');
 await page.getByRole('textbox',{name:text('value'),exact:true}).fill('Missing');await page.getByRole('button',{name:text('applyFilter'),exact:true}).click();
 await expect(page.getByRole('gridcell',{name:'Silver',exact:true})).not.toBeVisible();
 await page.getByRole('button',{name:text('resetFilter'),exact:true}).click();await expect(page.getByRole('gridcell',{name:'Silver',exact:true})).toBeVisible();
 await page.locator('summary').filter({hasText:text('columns')}).click();await page.getByRole('checkbox',{name:'Loyalty',exact:true}).uncheck();
 await expect(page.getByRole('columnheader',{name:'Loyalty',exact:true})).not.toBeVisible();await page.getByRole('checkbox',{name:'Loyalty',exact:true}).check();
 await page.goto(`/app/business/services?service=${service.id}`);
 await expect(page.getByTestId('service-edit-modal')).toBeVisible();
 await expect(page.getByRole('spinbutton',{name:'Rating',exact:true})).toHaveValue('4');
 await page.getByRole('spinbutton',{name:'Rating',exact:true}).fill('5');
 const customSaved=page.waitForResponse(r=>r.url().includes('/custom-field-values/bulk-upsert/')&&r.request().method()==='POST');
 await page.getByRole('button',{name:'Save fields',exact:true}).click();expect((await customSaved).ok()).toBeTruthy();
 await page.screenshot({path:`${output}/ui-service.png`,fullPage:true});
 await page.goto('/app/calendar?date=2026-12-14&view=week');
 await page.locator('[data-calendar-day="2026-12-14"]').click();
 await expect(page.getByTestId('calendar-day-inspector').getByText('Room: Room A',{exact:true})).toBeVisible();
 await page.screenshot({path:`${output}/ui-live-calendar.png`,fullPage:true});
 expect(errors).toEqual([]);
 fs.writeFileSync(`${output}/ui-result.json`,JSON.stringify({workspace:id,client:client.id,service:service.id}));
});

for (const lang of ['ru','kk']) test(`localized mobile draft and keyboard ${lang}`,async({page})=>{
 await page.setViewportSize({width:390,height:844});await login(page,lang);
 await expect(page.getByRole('heading',{name:text('title',lang),exact:true})).toBeVisible();
 await emptyDraft(page);
 await expect(page).toHaveURL(/draft=\d+/);
 const selector=page.getByRole('combobox',{name:new RegExp('^'+text('entity',lang)+' ')}).first();
 await selector.focus();await page.keyboard.press('Enter');await expect(page.getByRole('listbox')).toBeVisible();
 await page.keyboard.press('Escape');await expect(page.getByRole('listbox')).not.toBeVisible();await expect(selector).toBeFocused();
 await page.getByRole('button',{name:text('cancel',lang),exact:true}).click();
 await page.keyboard.press('Escape');await expect(page.getByRole('dialog')).not.toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1)).toBeTruthy();
 await page.screenshot({path:`${output}/ui-mobile-${lang}.png`,fullPage:true});
});

test('source errors, exclusion, unsaved navigation and recovery',async({page})=>{
 await login(page);await emptyDraft(page);
 await expect(page).toHaveURL(/draft=\d+/);
 await addSource(page,'clients','invalid.csv','full_name,email\nRecovery Client,invalid-email\n');await save(page);
 await page.getByRole('button',{name:text('check'),exact:true}).click();
 await expect(page.getByRole('button',{name:text('confirm'),exact:true})).toBeDisabled();
 await expect(page.getByRole('heading',{name:new RegExp('^'+text('errors'))})).toBeVisible({timeout:30000});
 await page.getByRole('button',{name:'invalid.csv · '+text('row')+' 1',exact:true}).click();
 const editor=page.getByRole('dialog');await editor.getByRole('textbox',{name:'email',exact:true}).fill('recovery@example.test');
 await editor.getByRole('button',{name:text('save'),exact:true}).click();
 await page.locator('main').getByRole('link',{name:'Connections',exact:true}).click();
 await expect(page.getByRole('dialog')).toBeVisible();await page.keyboard.press('Escape');
 await expect(page.getByRole('dialog')).not.toBeVisible();await save(page);
 let once=true;await page.route('**/api/import-workspaces/*/preview/',async route=>{if(once){once=false;await route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'Temporary test failure'})});}else await route.continue();});
 await page.getByRole('button',{name:text('check'),exact:true}).click();await expect(page.getByRole('alert').first()).toBeVisible();
 await page.getByRole('button',{name:text('check'),exact:true}).click();
 await expect(page.getByRole('button',{name:text('confirm'),exact:true})).toBeEnabled({timeout:30000});
 await page.getByRole('button',{name:text('card'),exact:true}).click();await expect(page.getByRole('dialog').getByRole('textbox').first()).toHaveValue('Recovery Client');
 await page.keyboard.press('Escape');await expect(page.getByRole('dialog')).not.toBeVisible();
});

test('view-only member cannot open transfer workspace',async({page})=>{
 await login(page,'en','import-viewer@example.test');
 await expect(page.getByRole('button',{name:text('new'),exact:true})).not.toBeVisible();
 await expect(page.locator('main')).not.toContainText(text('history'));
});


test('failed source refresh hides cached row values until recovery',async({page})=>{
 await login(page);await emptyDraft(page);await expect(page).toHaveURL(/draft=\d+/);
 await addSource(page,'clients','cache.csv','full_name\nCached Private Source\n');await save(page);
 await page.getByRole('button',{name:text('data'),exact:true}).click();await expect(page.getByRole('cell',{name:'Cached Private Source',exact:true})).toBeVisible();
 await page.getByRole('button',{name:text('fields'),exact:true}).click();
 const deny=async route=>route.fulfill({status:403,contentType:'application/json',body:JSON.stringify({code:'permission_denied',detail:'Denied'})});
 await page.route('**/api/import-workspaces/*/rows/**',deny);
 await page.getByRole('button',{name:text('data'),exact:true}).click();await expect(page.getByRole('button',{name:text('reload'),exact:true})).toBeVisible();
 await expect(page.getByRole('cell',{name:'Cached Private Source',exact:true})).not.toBeVisible();
 await page.unroute('**/api/import-workspaces/*/rows/**',deny);await page.getByRole('button',{name:text('reload'),exact:true}).click();
 await expect(page.getByRole('cell',{name:'Cached Private Source',exact:true})).toBeVisible();
});


test('explicit overwrite shows before/after and saved profile prevents repeated writes',async({page})=>{
 const token=await login(page);const client=await post(page,token,'clients/',{business:fixture.business,full_name:'Before Update',email:'update-import@example.test'});
 await emptyDraft(page);await expect(page).toHaveURL(/draft=\d+/);
 const id=Number(new URL(page.url()).searchParams.get('draft'));
 const csv='external_id,full_name,email\nU1,After Update,update-import@example.test\n';
 await addSource(page,'clients','update.csv',csv);await save(page);
 await page.getByRole('textbox',{name:text('profileName'),exact:true}).fill('Reusable update');await page.getByRole('button',{name:text('saveProfile'),exact:true}).click();await expect(page.getByRole('textbox',{name:text('profileName'),exact:true})).toHaveValue('');
 await page.getByRole('button',{name:text('data'),exact:true}).click();await page.getByRole('button',{name:`${text('edit')}: ${text('row')} 1`,exact:true}).click();
 const dialog=page.getByRole('dialog');await choose(page,dialog.getByRole('combobox',{name:new RegExp('^'+text('decision')+' ')}),text('update'));
 await dialog.getByRole('textbox',{name:text('target'),exact:true}).fill('Before Update');await dialog.getByRole('button').filter({hasText:'Before Update'}).click();
 await dialog.getByRole('checkbox',{name:text('field.full_name'),exact:true}).check();await dialog.getByRole('button',{name:text('save'),exact:true}).click();await save(page);
 await page.getByRole('button',{name:text('check'),exact:true}).click();await expect(page.getByRole('button',{name:text('confirm'),exact:true})).toBeEnabled({timeout:30000});
 await page.getByRole('button',{name:text('card'),exact:true}).click();await expect(page.getByRole('dialog').getByText('Before Update',{exact:true})).toBeVisible();await expect(page.getByRole('dialog').getByRole('cell',{name:'After Update',exact:true})).toBeVisible();await page.keyboard.press('Escape');
 await page.getByRole('button',{name:text('confirm'),exact:true}).click();await page.getByRole('dialog').getByRole('button',{name:text('confirm'),exact:true}).click();
 await expect(page.getByRole('button',{name:text('activateReview'),exact:true})).toBeVisible({timeout:30000});
 const current=await page.request.get(`${process.env.E2E_API_BASE_URL}/api/clients/${client.id}/`,{headers:{Authorization:`Bearer ${token}`}});expect((await current.json()).full_name).toBe('After Update');
 const first=await page.request.get(`${process.env.E2E_API_BASE_URL}/api/import-workspaces/${id}/`,{headers:{Authorization:`Bearer ${token}`}});expect((await first.json()).result.summary.updated).toBe(1);
 await emptyDraft(page);
 const chooser=page.waitForEvent('filechooser');await page.getByRole('button',{name:text('upload'),exact:true}).click();await chooser;
 const uploaded=page.waitForResponse(r=>r.url().endsWith('/upload/')&&r.request().method()==='POST');await page.locator('input[type=file]').setInputFiles({name:'update.csv',mimeType:'text/csv',buffer:Buffer.from(csv)});await uploaded;
 await choose(page,page.getByRole('combobox',{name:new RegExp('^'+text('profiles')+' ')}),'Reusable update · '+text('clients'));await page.getByRole('button',{name:text('applyProfile'),exact:true}).click();
 await page.getByRole('button',{name:text('check'),exact:true}).click();await expect(page.getByRole('button',{name:text('confirm'),exact:true})).toBeEnabled({timeout:30000});
 const repeatedId=Number(new URL(page.url()).searchParams.get('draft'));const repeated=await page.request.get(`${process.env.E2E_API_BASE_URL}/api/import-workspaces/${repeatedId}/`,{headers:{Authorization:`Bearer ${token}`}});expect((await repeated.json()).report.summary.unchanged).toBe(1);
});
