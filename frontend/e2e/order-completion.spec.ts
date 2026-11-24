import {test,expect} from "@playwright/test";
import {execFileSync} from "node:child_process";
import {ru} from "../src/lib/i18n/ru";
import {kk} from "../src/lib/i18n/kk";
import {openClinicalWorkspace} from "./clinical-card-navigation";
import {requireIsolatedEnvironment} from "./isolated-environment.mjs";
requireIsolatedEnvironment();
for(const locale of ["ru","kk"] as const)test(`approved completion ${locale}: accept retains source and rejects late reply`,async({page},info)=>{
 const t=locale==="ru"?ru:kk;
 const entry=JSON.parse(execFileSync(process.env.E2E_PYTHON!,["e2e/clinical-runtime.py","order-completion-prepare"],{env:process.env,windowsHide:true,encoding:"utf8"}).trim().split(/\r?\n/).at(-1)!);
 await page.addInitScript(language=>localStorage.setItem("ai_smb_language",language),locale);await page.goto("/login");
 await page.locator('input[name="email"]').fill(entry.email);await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
 const login=page.waitForResponse(r=>r.url().includes("/api/auth/token/")&&r.request().method()==="POST");await page.locator('form button[type="submit"]').click();const token=(await(await login).json()).access;await expect(page).toHaveURL(/\/app\//);
 const appointment=await(await page.request.get(`${process.env.E2E_API_BASE_URL}/api/appointments/${entry.appointment_id}/`,{headers:{Authorization:`Bearer ${token}`}})).json();
 await page.goto(`/app/calendar?appointment=${entry.appointment_id}&date=${appointment.start_at.slice(0,10)}&view=day`);await openClinicalWorkspace(page);
 const workspace=page.getByTestId("clinical-workspace");await workspace.getByRole("tab",{name:t["medical.orders.title"],exact:true}).click();
 const orders=workspace.getByTestId("medical-orders");await orders.getByRole("button",{name:t["medical.orders.create"],exact:true}).click();
 const editor=page.getByTestId("medical-order-editor");const input=editor.getByRole("textbox",{name:t["medical.orders.text"],exact:true});
 await input.fill(entry.prefix);
 async function choose(){
  await editor.getByRole("button",{name:t["medical.documents.chooseTemplate"],exact:true}).click();
  const picker=page.getByTestId("order-template-picker");await picker.getByRole("button",{name:new RegExp(entry.title)}).click();
  await expect(picker.getByRole("textbox",{name:t["medical.orders.text"],exact:true})).toHaveValue(entry.expected);
  await picker.getByRole("button",{name:t["medical.assistance.useCompletion"],exact:true}).click();await expect(picker).toHaveCount(0);
 }
 await choose();const completion=editor.getByTestId("order-template-completion");await expect(input).toHaveValue(entry.prefix);
 await input.focus();await page.keyboard.press("Escape");await expect(editor).toBeVisible();await expect(completion.getByRole("button",{name:t["medical.assistance.accept"],exact:true})).toHaveCount(0);
 await choose();await input.fill("Nonmatching manual text");await expect(completion).toContainText(t["medical.assistance.noContinuation"]);await input.fill(entry.prefix);
 await expect(completion.getByTestId("order-template-ghost")).toBeVisible();await expect(completion.getByTestId("order-template-ghost")).toContainText(entry.expected);
 await page.setViewportSize({width:1440,height:1000});await editor.screenshot({path:info.outputPath("completion-desktop.png")});await page.setViewportSize({width:390,height:844});await editor.screenshot({path:info.outputPath("completion-mobile.png")});
 const path="**/api/medical/orders/preview/**";
 let started!:()=>void,release!:()=>void,finished!:()=>void;const began=new Promise<void>(r=>started=r),held=new Promise<void>(r=>release=r),done=new Promise<void>(r=>finished=r);
 await page.route(path,async route=>{const response=await route.fetch();started();await held;await route.fulfill({response}).catch(()=>{});finished();});
 await completion.getByRole("button",{name:t["medical.assistance.accept"],exact:true}).click();await began;await input.fill("Keep this newer input");release();await done;await expect(input).toHaveValue("Keep this newer input");await page.unroute(path);await input.fill(entry.prefix);
 await page.route(path,route=>route.fulfill({status:503,json:{detail:"Synthetic unavailable"}}));await completion.getByRole("button",{name:t["medical.assistance.accept"],exact:true}).click();await expect(completion.getByRole("alert")).toHaveText(t["medical.assistance.templateChanged"]);await expect(input).toHaveValue(entry.prefix);await page.unroute(path);
 if(locale==="ru"){await input.focus();await page.keyboard.press("Tab");}else await completion.getByRole("button",{name:t["medical.assistance.accept"],exact:true}).click();
 await expect(input).toHaveValue(entry.expected);await expect(input).toBeFocused();await expect(editor.getByTestId("order-template-source")).toContainText(entry.title);
 await editor.getByRole("button",{name:t["medical.clinical.save"],exact:true}).click();await expect(editor).toHaveCount(0);await expect(orders.getByTestId("order-template-source")).toContainText(entry.title);
 if(locale==="kk"){
  await orders.getByRole("button",{name:t["common.edit"],exact:true}).click();await input.fill(entry.prefix);await choose();
  await page.route(path,route=>route.fulfill({status:403,json:{detail:"Synthetic revoked"}}));await completion.getByRole("button",{name:t["medical.assistance.accept"],exact:true}).click();await expect(editor).toHaveCount(0);await expect(orders.getByRole("alert")).toBeVisible();
 }
});
