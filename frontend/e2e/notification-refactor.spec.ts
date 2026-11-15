import { expect, test } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
for (const [language, width, copy] of [["ru", 1440, ru], ["kk", 390, kk]] as const) {
 test(`notification bell retains read recovery, read-all, keyboard and center synchronization ${language}`, async ({page},info)=>{
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Disposable authentication fixture required");
  await page.setViewportSize({width,height:900});
  const session=await crmSession(page);let readFailure=true;let summaryReads=0;
  const notices=[1,2].map(id=>({id,business:session.business,recipient:session.userId,recipient_name:'',recipient_email:'',client_name:'',kind:'work_item',text:`Refactor notice ${id}`,message:`Refactor notice ${id}`,category:'system',priority:'normal',read_at:null as string|null,send_at:'2026-10-30T01:00:00Z',action_url:'',action_label:''}));
  const writes:string[]=[];
  await page.route('**/api/notifications/**',async route=>{
   const request=route.request(),url=new URL(request.url());
   expect(url.searchParams.get('business')).toBe(String(session.business));
   if(request.method()==='POST'){
    writes.push(url.pathname);
    if(url.pathname.endsWith('/mark-all-read/')){notices.forEach(n=>n.read_at='2026-10-30T02:00:00Z');return route.fulfill({json:{updated:2}});}
    if(url.pathname.endsWith('/mark-read/')){if(readFailure)return route.fulfill({status:503,json:{detail:'Read fixture unavailable'}});const n=notices.find(n=>url.pathname.includes(`/${n.id}/`))!;n.read_at='2026-10-30T02:00:00Z';return route.fulfill({json:n});}
    throw new Error(`Unexpected write ${url.pathname}`);
   }
   if(url.pathname.endsWith('/summary/')){summaryReads++;return route.fulfill({json:{unread:notices.filter(n=>!n.read_at).length,due:0,urgent:0,pending:0,failed:0,by_category:{system:2},can_manage_announcements:false}});}
   return route.fulfill({json:{count:2,next:null,previous:null,results:notices}});
  });
  await page.evaluate(value=>localStorage.setItem('ai_smb_language',value),language);await page.goto('/app/notifications');
  await expect(page.getByTestId('notification-feed-row')).toHaveCount(2);
  const menu=page.getByTestId('notification-menu');
  const bell=page.getByTestId('header-notifications-trigger');await expect(bell).toContainText('2');await bell.focus();await page.keyboard.press('Enter');
  await expect(menu.getByText('Refactor notice 1',{exact:true})).toBeVisible();
  await page.screenshot({path:info.outputPath(`notification-bell-${language}.png`),fullPage:true});
  await menu.getByRole('button',{name:copy['notification.markRead'],exact:true}).first().click();await expect(menu.getByRole('alert').first()).toBeVisible();
  readFailure=false;await menu.getByRole('button',{name:copy['notification.markRead'],exact:true}).first().click();await expect(bell).toContainText('1');
  await menu.getByRole('button',{name:copy['header.markAllRead'],exact:true}).click();await expect(bell).not.toContainText('1');
  await page.keyboard.press('Escape');await expect(page.getByRole('link',{name:copy['notification.openCenter'],exact:true})).toHaveCount(0);
  await bell.click();await page.getByRole('link',{name:copy['notification.openCenter'],exact:true}).click();await expect(page).toHaveURL(/\/app\/notifications/);
  expect(writes).toHaveLength(3);expect(summaryReads).toBeGreaterThanOrEqual(3);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();
 });
}
