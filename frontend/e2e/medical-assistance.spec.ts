import {test,expect} from "@playwright/test";
import {execFileSync} from "node:child_process";
import {ru} from "../src/lib/i18n/ru";
import {kk} from "../src/lib/i18n/kk";
import {openClinicalWorkspace} from "./clinical-card-navigation";
import {requireIsolatedEnvironment} from "./isolated-environment.mjs";
requireIsolatedEnvironment();

for(const locale of ["ru","kk"] as const)test(`current field assistance ${locale}: preview accept stale and denial`,async({page},info)=>{
 page.on("console",message=>{if(message.text().startsWith("AUDIO_DIAGNOSTIC"))console.log(message.text());});
 await page.addInitScript(()=>{const media=navigator.mediaDevices;if(media){const original=media.getUserMedia.bind(media);media.getUserMedia=async constraints=>{try{const stream=await original(constraints);console.log("AUDIO_DIAGNOSTIC media ready");for(const track of stream.getTracks()){for(const event of ["mute","ended"])track.addEventListener(event,()=>console.log("AUDIO_DIAGNOSTIC track "+event));}return stream;}catch(error){console.log("AUDIO_DIAGNOSTIC "+(error instanceof Error?error.name:"unknown"));throw error;}};}});
 const t=locale==="ru"?ru:kk;
 const entry=JSON.parse(execFileSync(process.env.E2E_PYTHON!,["e2e/clinical-runtime.py","completion-prepare"],{env:process.env,windowsHide:true,encoding:"utf8"}).trim().split(/\r?\n/).at(-1)!);
 await page.addInitScript(language=>localStorage.setItem("ai_smb_language",language),locale);await page.goto("/login");
 await page.locator('input[name="email"]').fill(entry.email);await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
 const login=page.waitForResponse(r=>r.url().includes("/api/auth/token/")&&r.request().method()==="POST");await page.locator('form button[type="submit"]').click();const token=(await(await login).json()).access;await expect(page).toHaveURL(/\/app\//);
 const appointment=await(await page.request.get(`${process.env.E2E_API_BASE_URL}/api/appointments/${entry.appointment_id}/`,{headers:{Authorization:`Bearer ${token}`}})).json();
 await page.goto(`/app/calendar?appointment=${entry.appointment_id}&date=${appointment.start_at.slice(0,10)}&view=day`);await openClinicalWorkspace(page);
 const workspace=page.getByTestId("clinical-workspace");await workspace.getByRole("tab",{name:t["medical.clinical.note"],exact:true}).click();
 const input=workspace.getByRole("textbox",{name:t["medical.clinical.complaints"],exact:true});const original=locale==="ru"?"Зуб 16 боли нет доза 1,5 мг":"16 тіс ауырмайды мөлшері 1,5 мг";
 await input.fill(original);const assistance=workspace.getByTestId("clinical-assistance-complaints");const request=assistance.getByRole("button",{name:t["medical.assistance.format"],exact:true});
 await request.click();const preview=assistance.getByRole("region",{name:t["medical.assistance.preview"],exact:true});await expect(preview).toBeVisible();await expect(input).toHaveValue(original);
 await page.setViewportSize({width:1440,height:1000});await assistance.scrollIntoViewIfNeeded();await page.screenshot({path:info.outputPath("assistance-desktop.png")});await page.setViewportSize({width:390,height:844});await assistance.scrollIntoViewIfNeeded();await page.screenshot({path:info.outputPath("assistance-mobile.png")});
 await preview.focus();await page.keyboard.press("Escape");await expect(preview).toHaveCount(0);await expect(input).toHaveValue(original);
 await request.click();await expect(preview).toBeVisible();if(locale==="ru"){await preview.focus();await page.keyboard.press("Tab");}else await preview.getByRole("button",{name:t["medical.assistance.accept"],exact:true}).click();
 await expect(input).toHaveValue(original+".");
 await assistance.getByRole("button",{name:t["medical.assistance.dictate"],exact:true}).click();
 const stop=assistance.getByRole("button",{name:locale==="ru"?/Остановить · [1-9]/:/Тоқтату · [1-9]/});await expect(stop).toBeVisible();await stop.click();
 await expect(preview).toBeVisible();await expect(input).toHaveValue(original+".");await preview.getByRole("button",{name:t["medical.assistance.accept"],exact:true}).click();
 await expect(input).toHaveValue(original+".\n"+(locale==="ru"?"Зуб 16 не болит":"16 тіс ауырмайды"));
 await page.screenshot({path:info.outputPath("dictation-accepted.png")});
 await request.click();await expect(preview).toBeVisible();await input.fill(original+" жаңа");await expect(preview).toHaveCount(0);
 const path="**/api/medical/assistance/suggest/";
 let release!:()=>void;let started!:()=>void;const received=new Promise<void>(resolve=>started=resolve);const held=new Promise<void>(resolve=>release=resolve);
 await page.route(path,async route=>{const response=await route.fetch();started();await held;await route.fulfill({response}).catch(()=>{});});
 await request.click();await received;await input.fill(original+" новый ввод");release();await expect(preview).toHaveCount(0);await expect(input).toHaveValue(original+" новый ввод");await page.unroute(path);await input.fill(original+" жаңа");
await page.route(path,route=>route.fulfill({status:503,json:{detail:"Synthetic unavailable"}}));await request.click();await expect(assistance.getByRole("status")).toContainText(t["medical.assistance.unavailable"]);await expect(input).toHaveValue(original+" жаңа");await page.unroute(path);
 if(locale==="kk"){await page.route(path,route=>route.fulfill({status:403,json:{detail:"Synthetic revoked"}}));await request.click();await expect(input).toHaveCount(0);await expect(workspace).toContainText(t["medical.denied"]);}
 else{await workspace.getByRole("button",{name:t["medical.clinical.save"],exact:true}).click();await expect(input).toHaveValue(original+" жаңа");await expect(workspace.getByRole("status")).toContainText(t["common.saved"]);}
});
