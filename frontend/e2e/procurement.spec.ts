import { test, expect } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { openClinicalWorkspace } from "./clinical-card-navigation";
import { requireIsolatedEnvironment } from "./isolated-environment.mjs";
requireIsolatedEnvironment();

test("doctor creates, edits and cancels own material request without patient context", async ({page}, info)=>{
 const entry=JSON.parse(execFileSync(process.env.E2E_PYTHON!,["e2e/clinical-runtime.py","completion-prepare"],{env:process.env,windowsHide:true,encoding:"utf8"}).trim().split(/\r?\n/).at(-1)!);
 await page.addInitScript(()=>localStorage.setItem("ai_smb_language","ru"));await page.goto("/login");
 await page.locator('input[name="email"]').fill(entry.email);await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
 await page.locator('form button[type="submit"]').click();await expect(page).toHaveURL(/\/app\//);
 const widget=page.getByTestId("purchase-entry");await widget.getByRole("button",{name:ru["procurement.create"],exact:true}).click();
 const dialog=page.getByRole("dialog",{name:ru["procurement.create"],exact:true});
 const material=`Synthetic material ${Date.now()}`;
 await dialog.getByRole("textbox",{name:ru["procurement.material"],exact:true}).fill(material);
 await dialog.getByRole("textbox",{name:ru["procurement.specification"],exact:true}).fill("Synthetic size 12");
 await dialog.getByLabel(ru["procurement.quantity"],{exact:true}).fill("10");
 await dialog.getByRole("textbox",{name:ru["procurement.comment"],exact:true}).fill("Synthetic organizational request");
 await page.setViewportSize({width:1440,height:1100});await page.screenshot({path:info.outputPath("purchase-desktop.png")});
 await page.setViewportSize({width:390,height:844});await page.screenshot({path:info.outputPath("purchase-mobile.png")});
 const save=dialog.getByRole("button",{name:ru["procurement.submit"],exact:true});
 await page.route("**/api/procurement/requests/",route=>route.request().method()==="POST"?route.fulfill({status:503,json:{detail:"Synthetic unavailable"}}):route.continue());
 await save.click();await expect(dialog.getByRole("alert")).toBeVisible();await expect(dialog.getByRole("textbox",{name:ru["procurement.material"],exact:true})).toHaveValue(material);
 await page.unroute("**/api/procurement/requests/");const response=page.waitForResponse(r=>r.url().endsWith("/procurement/requests/")&&r.request().method()==="POST");await save.click();const item=await(await response).json();await expect(dialog).toHaveCount(0);
 await widget.getByRole("button",{name:ru["procurement.mine"],exact:true}).click();
 const mine=page.getByRole("dialog",{name:ru["procurement.mine"],exact:true});const row=mine.getByTestId(`purchase-request-${item.id}`);await expect(row).toContainText(material);
 await row.getByRole("button",{name:ru["common.edit"],exact:true}).click();await mine.getByLabel(ru["procurement.quantity"],{exact:true}).fill("12");
 await mine.getByRole("textbox",{name:ru["procurement.reason"],exact:true}).fill("Synthetic quantity correction");await mine.getByRole("button",{name:ru["common.save"],exact:true}).click();await expect(row).toContainText("12.000");
 await row.getByRole("button",{name:ru["procurement.cancelRequest"],exact:true}).click();await mine.getByRole("textbox",{name:ru["procurement.reason"],exact:true}).fill("Synthetic no longer required");await mine.getByRole("button",{name:ru["procurement.cancelRequest"],exact:true}).click();
 await expect(row).toContainText(ru["procurement.state.cancelled"]);await row.locator("summary").click();await expect(row).toContainText("Synthetic quantity correction");await expect(row).toContainText("Synthetic no longer required");
 await page.screenshot({path:info.outputPath("purchase-history-mobile.png")});
});

for(const mode of ["yes","no"] as const)test(`completion exit offers same request form once ${mode}`,async({page},info)=>{
 const t=mode==="yes"?ru:kk;
 const entry=JSON.parse(execFileSync(process.env.E2E_PYTHON!,["e2e/clinical-runtime.py","completion-prepare"],{env:process.env,windowsHide:true,encoding:"utf8"}).trim().split(/\r?\n/).at(-1)!);
 await page.addInitScript(language=>localStorage.setItem("ai_smb_language",language),mode==="yes"?"ru":"kk");await page.goto("/login");
 await page.locator('input[name="email"]').fill(entry.email);await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
 const login=page.waitForResponse(r=>r.url().includes("/api/auth/token/")&&r.request().method()==="POST");await page.locator('form button[type="submit"]').click();const token=(await(await login).json()).access;
 await expect(page).toHaveURL(/\/app\//);
 const appointment=await(await page.request.get(`${process.env.E2E_API_BASE_URL}/api/appointments/${entry.appointment_id}/`,{headers:{Authorization:`Bearer ${token}`}})).json();
 await page.goto(`/app/calendar?appointment=${entry.appointment_id}&date=${appointment.start_at.slice(0,10)}&view=day`);await openClinicalWorkspace(page);
 const workspace=page.getByTestId("clinical-workspace");await workspace.getByRole("tab",{name:t["medical.clinical.note"],exact:true}).click();
 for(const field of ["complaints","anamnesis","allergies","contraindications","examination","diagnosis","procedures","plan","epicrisis"] as const)await workspace.getByRole("textbox",{name:t[`medical.clinical.${field}`],exact:true}).fill(`Synthetic ${field} ${entry.appointment_id}`);
 await workspace.getByRole("button",{name:t["medical.clinical.save"],exact:true}).click();await expect(workspace.getByRole("button",{name:t["medical.completion.title"],exact:true})).toBeEnabled();
 await workspace.getByRole("button",{name:t["medical.completion.title"],exact:true}).click();const completion=workspace.getByTestId("encounter-completion");
 await completion.getByRole("textbox",{name:t["medical.completion.earlyReason"],exact:true}).fill("Synthetic completed work");
 await completion.getByRole("button",{name:t["medical.completion.confirm"],exact:true}).click();await expect(page.getByTestId("encounter-completed")).toBeVisible();
 await expect(page.getByRole("dialog",{name:t["procurement.prompt.title"],exact:true})).toHaveCount(0);
 await page.keyboard.press("Escape");
 const offer=page.getByRole("dialog",{name:t["procurement.prompt.title"],exact:true});await expect(offer).toBeVisible();
 await page.setViewportSize({width:1440,height:1000});await page.screenshot({path:info.outputPath("prompt-desktop.png")});await page.setViewportSize({width:390,height:844});await page.screenshot({path:info.outputPath("prompt-mobile.png")});
 if(mode==="no")await offer.getByRole("button",{name:t["procurement.prompt.no"],exact:true}).click();
 else{
  await offer.getByRole("button",{name:t["procurement.prompt.yes"],exact:true}).click();const form=page.getByRole("dialog",{name:t["procurement.create"],exact:true});
  await form.getByRole("textbox",{name:t["procurement.material"],exact:true}).fill(`Synthetic post-visit ${entry.appointment_id}`);await form.getByLabel(t["procurement.quantity"],{exact:true}).fill("2");
  await form.getByRole("button",{name:t["procurement.submit"],exact:true}).click();await expect(form).toHaveCount(0);
 }
 await expect(offer).toHaveCount(0);await page.reload();await expect(page.getByTestId("calendar-workspace-ready")).toBeVisible();await expect(offer).toHaveCount(0);
 const saved=await(await page.request.get(`${process.env.E2E_API_BASE_URL}/api/appointments/${entry.appointment_id}/`,{headers:{Authorization:`Bearer ${token}`}})).json();expect(saved.status).toBe("completed");
});

test("KK request conflict reload and revoked access clear the form",async({page},info)=>{
 const entry=JSON.parse(execFileSync(process.env.E2E_PYTHON!,["e2e/clinical-runtime.py","completion-prepare"],{env:process.env,windowsHide:true,encoding:"utf8"}).trim().split(/\r?\n/).at(-1)!);
 await page.addInitScript(()=>localStorage.setItem("ai_smb_language","kk"));await page.goto("/login");
 await page.locator('input[name="email"]').fill(entry.email);await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);await page.locator('form button[type="submit"]').click();await expect(page).toHaveURL(/\/app\//);
 const widget=page.getByTestId("purchase-entry");
 async function fill(){await widget.getByRole("button",{name:kk["procurement.create"],exact:true}).click();const form=page.getByRole("dialog",{name:kk["procurement.create"],exact:true});await form.getByRole("textbox",{name:kk["procurement.material"],exact:true}).fill("Synthetic KK material");await form.getByLabel(kk["procurement.quantity"],{exact:true}).fill("5");return form;}
 let form=await fill();const path="**/api/procurement/requests/";
 await page.setViewportSize({width:390,height:844});await page.screenshot({path:info.outputPath("request-kk-mobile.png")});
 await page.route(path,route=>route.fulfill({status:409,json:{detail:"Synthetic conflict"}}));await form.getByRole("button",{name:kk["procurement.submit"],exact:true}).click();await expect(form.getByRole("button",{name:kk["procurement.submit"],exact:true})).toBeDisabled();
 page.once("dialog",dialog=>dialog.accept());await form.getByRole("button",{name:kk["medical.clinical.reload"],exact:true}).click();await expect(form).toHaveCount(0);await page.unroute(path);
 form=await fill();await page.route(path,route=>route.fulfill({status:403,json:{detail:"Synthetic revoked"}}));await form.getByRole("button",{name:kk["procurement.submit"],exact:true}).click();await expect(form).toHaveCount(0);await expect(widget.getByRole("button",{name:kk["procurement.create"],exact:true})).toHaveCount(0);await expect(widget.getByRole("alert")).toBeVisible();
});
