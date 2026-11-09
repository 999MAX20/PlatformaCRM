const {test,expect}=require('@playwright/test');
const path=require('path');
const out=process.env.IMPORT_WORKSPACE_OUTPUT || path.resolve(__dirname,'../../output/import-new-picker-20261106');
const file=path.resolve(__dirname,'fixtures/import-clients.xlsx');
const label=(lang,key)=>require(`../src/lib/i18n/${lang}/importWorkspace.ts`).importWorkspace[`importWorkspace.${key}`];
async function login(page,lang){
 await page.addInitScript(lang=>localStorage.setItem('ai_smb_language',lang),lang);
 await page.route('**/api/auth/me/',async route=>{const response=await route.fetch();const user=await response.json();await route.fulfill({response,json:{...user,preferences:{...user.preferences,language:lang}}});});
 await page.goto('/login');await page.locator('input[type=email]').fill('business_owner@example.com');await page.locator('input[type=password]').fill(process.env.E2E_PASSWORD);const tokenResponse=page.waitForResponse(r=>r.url().endsWith('/api/auth/token/')&&r.request().method()==='POST');await page.locator('form button[type=submit]').click();const token=(await(await tokenResponse).json()).access;await expect(page.getByTestId('header-account-link')).toBeVisible();await page.goto('/app/integrations/import');return token;
}
async function chooser(page,lang,key){
 const opened=page.waitForEvent('filechooser');await page.getByRole('button',{name:label(lang,key),exact:true}).focus();await page.keyboard.press('Enter');return opened;
}
const uploadResponse=page=>page.waitForResponse(r=>r.url().endsWith('/upload/')&&r.request().method()==='POST');
test('complete original Excel transfer creates all twenty clients without duplicates',async({page})=>{
 test.setTimeout(180000);
 const expected=require('./fixtures/import-clients.expected.json');
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.setViewportSize({width:1440,height:1000});const token=await login(page,'ru');
 const headers={Authorization:`Bearer ${token}`};const api=process.env.E2E_API_BASE_URL+'/api/';
 const read=async url=>{const response=await page.request.get(api+url,{headers});expect(response.ok(),await response.text()).toBeTruthy();return response.json();};
 const selected=await chooser(page,'ru','new');const uploaded=uploadResponse(page);await selected.setFiles(file);const response=await uploaded;expect(response.status()).toBe(200);let workspace=await response.json();const id=workspace.id;
 expect(workspace.sources).toHaveLength(1);expect(workspace.sources[0].total_rows).toBe(20);
 const clientsUrl=`clients/?business=${workspace.business}&search=test.client.`;
 const baseline=(await read(clientsUrl)).count;expect(baseline).toBe(0);
 await page.getByRole('button',{name:label('ru','suggestions'),exact:true}).click();
 const saved=page.waitForResponse(r=>r.url().endsWith('/save_source/')&&r.request().method()==='POST');await page.getByRole('button',{name:label('ru','save'),exact:true}).click();expect((await saved).ok()).toBeTruthy();
 await page.reload();await expect(page.getByRole('button',{name:label('ru','check'),exact:true})).toBeEnabled();
 await page.getByRole('button',{name:label('ru','data'),exact:true}).click();
 await expect(page.getByRole('cell',{name:expected[0].full_name,exact:true})).toBeVisible();
 await page.getByRole('button',{name:label('ru','check'),exact:true}).click();
 await expect(page.getByRole('button',{name:label('ru','confirm'),exact:true})).toBeEnabled({timeout:45000});
 workspace=await read(`import-workspaces/${id}/`);expect(workspace.report.errors).toEqual([]);expect(workspace.report.rows).toHaveLength(20);expect(workspace.report.summary.created).toBe(20);
 for(const [index,row] of workspace.report.rows.entries()){const {external_id,...fields}=expected[index];expect(row.values).toMatchObject(fields);}
 expect((await read(clientsUrl)).count).toBe(baseline);
 await page.screenshot({path:`${out}/full-preview.png`,fullPage:true});
 await page.getByRole('button',{name:label('ru','confirm'),exact:true}).click();await page.keyboard.press('Escape');await expect(page.getByRole('dialog')).toHaveCount(0);expect((await read(clientsUrl)).count).toBe(baseline);
 await page.getByRole('button',{name:label('ru','confirm'),exact:true}).click();await page.getByRole('dialog').getByRole('button',{name:label('ru','confirm'),exact:true}).click();
 await expect(page.getByRole('button',{name:label('ru','activateReview'),exact:true})).toBeVisible({timeout:45000});
 workspace=await read(`import-workspaces/${id}/`);expect(workspace.state).toBe('imported');expect(workspace.result.summary.created).toBe(20);expect(workspace.result.rows).toHaveLength(20);
 const ids=workspace.result.rows.map(row=>row.id);expect(new Set(ids).size).toBe(20);expect((await read(clientsUrl)).count).toBe(baseline+20);
 for(const [index,id] of ids.entries()){const client=await read(`clients/${id}/`);const {external_id,...fields}=expected[index];expect(client).toMatchObject(fields);}
 const replay=await page.request.post(api+`import-workspaces/${id}/confirm/`,{headers,data:{version:workspace.version,background:true}});expect(replay.ok(),await replay.text()).toBeTruthy();expect((await read(clientsUrl)).count).toBe(baseline+20);
 await page.reload();await expect(page.getByRole('button',{name:label('ru','confirm'),exact:true})).toHaveCount(0);await expect(page.getByRole('button',{name:label('ru','activateReview'),exact:true})).toBeVisible();
 await page.getByRole('button',{name:label('ru','card'),exact:true}).first().click();await page.getByRole('dialog').getByRole('link',{name:label('ru','open'),exact:true}).click();
 await expect(page.getByRole('heading',{name:expected[0].full_name,exact:true})).toBeVisible();await expect(page.locator('main')).toContainText(expected[0].email);await expect(page.locator('main')).toContainText(expected[0].phone);await page.screenshot({path:`${out}/full-client-card.png`});
 await page.goto('/app/clients?search=test.client.');
 for(const row of expected)await expect(page.getByTestId('client-row-action-open').filter({hasText:row.full_name})).toBeVisible();
 await expect(page.getByTestId('client-row-action-open')).toHaveCount(20);await page.screenshot({path:`${out}/full-clients.png`,fullPage:true});
 await page.goto('/app/integrations/import');const repeatChooser=await chooser(page,'ru','new');const repeatUpload=uploadResponse(page);await repeatChooser.setFiles(file);const repeatedDraft=await(await repeatUpload).json();expect(repeatedDraft.id).not.toBe(id);
 await page.getByRole('button',{name:label('ru','suggestions'),exact:true}).click();const repeatSave=page.waitForResponse(r=>r.url().endsWith('/save_source/')&&r.request().method()==='POST');await page.getByRole('button',{name:label('ru','save'),exact:true}).click();expect((await repeatSave).ok()).toBeTruthy();
 await page.getByRole('button',{name:label('ru','check'),exact:true}).click();await expect(page.getByRole('button',{name:label('ru','confirm'),exact:true})).toBeEnabled({timeout:45000});
 const repeatedPreview=await read(`import-workspaces/${repeatedDraft.id}/`);expect(repeatedPreview.report.summary.unchanged).toBe(20);expect(repeatedPreview.report.summary.created).toBe(0);
 await page.getByRole('button',{name:label('ru','confirm'),exact:true}).click();await page.getByRole('dialog').getByRole('button',{name:label('ru','confirm'),exact:true}).click();await expect(page.getByRole('button',{name:label('ru','activateReview'),exact:true})).toBeVisible({timeout:45000});
 expect((await read(clientsUrl)).count).toBe(baseline+20);
 expect(errors).toEqual([]);
 require('fs').writeFileSync(`${out}/full-result.json`,JSON.stringify({workspace:id,clientIds:ids,verifiedFields:['full_name','phone','email','notes'],preview:20,created:20,replayCount:20,uiRows:20,repeatedFileUnchanged:20}));
});
for(const [lang,width] of [['ru',1440],['kk',390],['en',768]])test(`new chooser cancel select and append ${lang}`,async({page})=>{
 await page.setViewportSize({width,height:900});await login(page,lang);let creates=0;
 page.on('request',r=>{if(r.method()==='POST'&&r.url().endsWith('/api/import-workspaces/'))creates++;});
 const cancel=await chooser(page,lang,'new');await cancel.setFiles([]);expect(creates).toBe(0);await expect(page).not.toHaveURL(/draft=/);
 const selected=await chooser(page,lang,'new');const response=uploadResponse(page);await selected.setFiles(file);const uploaded=await response;expect(uploaded.status()).toBe(200);const first=await uploaded.json();expect(first.sources[0].total_rows).toBe(20);expect(creates).toBe(1);await expect(page).toHaveURL(new RegExp(`draft=${first.id}$`));await expect(page.getByRole('button',{name:label(lang,'upload'),exact:true})).toBeEnabled();
 const append=await chooser(page,lang,'upload');const appended=uploadResponse(page);await append.setFiles({name:'extra.csv',mimeType:'text/csv',buffer:Buffer.from('full_name\nExtra Client\n')});const second=await(await appended).json();expect(second.id).toBe(first.id);expect(second.sources).toHaveLength(2);expect(creates).toBe(1);
 await expect(page.getByRole('button',{name:label(lang,'new'),exact:true})).toBeEnabled();
 await page.getByRole('button',{name:label(lang,'suggestions'),exact:true}).click();await expect(page.getByRole('button',{name:label(lang,'new'),exact:true})).toBeDisabled();await expect(page.getByRole('button',{name:label(lang,'upload'),exact:true})).toBeDisabled();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();await page.screenshot({path:`${out}/picker-${lang}.png`});
});
test('failed new upload retains draft and same file retries without another draft',async({page})=>{
 await login(page,'en');let creates=0;page.on('request',r=>{if(r.method()==='POST'&&r.url().endsWith('/api/import-workspaces/'))creates++;});
 await page.route('**/api/import-workspaces/*/upload/',route=>route.fulfill({status:503,json:{code:'file_scan_unavailable',retryable:true}}));
 const selected=await chooser(page,'en','new');const failed=uploadResponse(page);await selected.setFiles(file);expect((await failed).status()).toBe(503);await expect(page.getByTestId('import-error-notice')).toBeVisible();const draftUrl=page.url();expect(draftUrl).toMatch(/draft=\d+/);expect(creates).toBe(1);
 await page.unroute('**/api/import-workspaces/*/upload/');const retry=await chooser(page,'en','upload');const success=uploadResponse(page);await retry.setFiles(file);expect((await success).status()).toBe(200);expect(creates).toBe(1);expect(page.url()).toBe(draftUrl);await expect(page.getByTestId('import-error-notice')).toHaveCount(0);
});
