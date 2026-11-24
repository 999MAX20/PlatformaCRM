import { openClinicalWorkspace } from "./clinical-card-navigation";
import { execFileSync } from "node:child_process";
import { test, expect } from "@playwright/test";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";
import { requireIsolatedEnvironment } from "./isolated-environment.mjs";
requireIsolatedEnvironment();

for (const [language, dictionary] of Object.entries({ ru, kk, en })) {
  for (const mobile of [false, true]) {
    test(`tooth chart ${language} ${mobile ? "mobile" : "desktop"}`, async ({ page }, info) => {
      test.setTimeout(90_000);
      const fixtureOutput = execFileSync(process.env.E2E_PYTHON!, ["e2e/clinical-runtime.py", "files-new-appointment"],
        { env: process.env, windowsHide: true, encoding: "utf8" });
      const id = JSON.parse(fixtureOutput.trim().split(/\r?\n/).at(-1)!).appointment_id;
      const t = (key: string) => dictionary[key as keyof typeof dictionary];
      await page.setViewportSize(mobile ? { width: 390, height: 844 } : { width: 1440, height: 1000 });
      await page.addInitScript(lang => localStorage.setItem("ai_smb_language", lang), language);
      await page.goto("/login");
      await page.locator('input[name="email"]').fill("medical-role-doctor@example.test");
      await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
      const login = page.waitForResponse(r => r.url().endsWith("/api/auth/token/") && r.request().method() === "POST");
      await page.locator('form button[type="submit"]').click();
      const token = (await (await login).json()).access;
      await expect(page).toHaveURL(/\/app\//);
      const headers = { Authorization: `Bearer ${token}` };
      const api = process.env.E2E_API_BASE_URL!;
      const context = await (await page.request.get(`${api}/api/medical/encounters/appointment-context/?business_id=1&appointment_id=${id}`, { headers })).json();
      const scope = { business_id: context.business_id, patient_id: context.patient.id };
      const record = await page.request.post(`${api}/api/medical/records/`, { headers: { ...headers, "Idempotency-Key": `tooth-record-${id}` },
        data: { ...scope, appointment_id: id, expected_patient_revision: 1, number: `TOOTH-${id}` } });
      expect(record.status()).toBe(201);
      const opened = await page.request.post(`${api}/api/medical/encounters/`, { headers: { ...headers, "Idempotency-Key": `tooth-open-${id}` },
        data: { ...scope, appointment_id: id, record_id: (await record.json()).id, expected_patient_revision: 1,
          expected_appointment_updated_at: context.appointment.updated_at } });
      expect(opened.status()).toBe(201);
      const encounterId = (await opened.json()).id;
      for (let revision = 0; revision < 2; revision++) {
        const saved = await page.request.post(`${api}/api/medical/tooth-observations/`, { headers: { ...headers, "Idempotency-Key": `tooth-${id}-${revision}` },
          data: { ...scope, encounter_id: encounterId, tooth: 11, expected_patient_revision: 1,
            expected_encounter_revision: 1, expected_tooth_revision: revision, observation: `Synthetic tooth version ${revision + 1}` } });
        expect(saved.status()).toBe(201);
      }
      await page.goto(`/app/calendar?appointment=${id}&date=${context.appointment.start_at.slice(0, 10)}`);
      await openClinicalWorkspace(page);
      const workspace = page.getByTestId("clinical-workspace");
      const complaint = workspace.getByLabel(t("medical.clinical.complaints"), { exact: true });
      if (language === "en" && mobile) {
        await complaint.fill("Saved clinical draft before tooth edit");
        await workspace.getByRole("button", { name: t("medical.clinical.save"), exact: true }).click();
        await expect(workspace.getByText(t("common.saved"), { exact: true })).toBeVisible();
      }
      await complaint.fill("Retain draft while reading teeth");
      await workspace.getByRole("tab", { name: t("medical.tooth.title"), exact: true }).click();
      const chart = page.getByTestId("tooth-chart");
      const tooth = chart.getByRole("button", { name: `${t("medical.tooth.tooth")} 11: ${t("medical.tooth.observed")}`, exact: true });
      await expect(tooth).toBeVisible();
      const box = await tooth.boundingBox();
      expect(box!.height).toBeGreaterThanOrEqual(44);
      expect(box!.width).toBeGreaterThanOrEqual(44);
      await workspace.screenshot({ path: info.outputPath("chart.png") });
      await tooth.click();
      const inspector = page.getByTestId("tooth-inspector");
      await expect(inspector.getByTestId("tooth-version")).toContainText("Synthetic tooth version 2");
      await inspector.locator('button[aria-pressed]').last().click();
      await expect(inspector.getByTestId("tooth-version")).toContainText("Synthetic tooth version 1");
      await inspector.screenshot({ path: info.outputPath("inspector.png") });
      await page.keyboard.press("Escape");
      await expect(inspector).not.toBeVisible();
      await expect(tooth).toBeFocused();
      await expect(workspace).toBeVisible();
      await tooth.click();
      const observation = inspector.getByLabel(t("medical.tooth.observation"), { exact: true });
      await observation.fill("Synthetic tooth saved from UI");
      await inspector.screenshot({ path: info.outputPath("editor.png") });
      await page.keyboard.press("Escape");
      const unsaved = page.getByTestId("tooth-unsaved");
      await expect(unsaved).toBeVisible();
      await unsaved.getByRole("button", { name: t("medical.clinical.continueEditing"), exact: true }).click();
      await expect(observation).toHaveValue("Synthetic tooth saved from UI");
      let rejectSave = language === "ru" && mobile;
      const keys: string[] = [];
      let releaseSave!: () => void;
      const saveRelease = new Promise<void>(resolve => { releaseSave = resolve; });
      if (rejectSave) await page.route("**/api/medical/tooth-observations/", async route => {
        if (route.request().method() !== "POST") return route.continue();
        keys.push(route.request().headers()["idempotency-key"]);
        if (rejectSave) await saveRelease;
        return rejectSave ? route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ code: "service_unavailable" }) }) : route.continue();
      });
      await page.keyboard.press("Escape");
      await unsaved.getByRole("button", { name: t("medical.clinical.saveClose"), exact: true }).click();
      if (rejectSave) {
        await expect.poll(() => keys.length).toBe(1);
        await expect(unsaved.getByRole("button", { name: t("medical.clinical.continueEditing"), exact: true })).toBeDisabled();
        await page.keyboard.press("Escape");
        await expect(unsaved).toBeVisible();
        expect(keys).toHaveLength(1);
        releaseSave();
        await expect(unsaved.getByRole("alert")).toBeVisible();
        await unsaved.getByRole("button", { name: t("medical.clinical.continueEditing"), exact: true }).click();
        await expect(observation).toHaveValue("Synthetic tooth saved from UI");
        rejectSave = false;
        await inspector.getByRole("button", { name: t("medical.tooth.save"), exact: true }).click();
      }
      await expect(inspector).not.toBeVisible();
      await expect(tooth).toBeFocused();
      if (keys.length) { expect(keys).toHaveLength(2); expect(keys[1]).toBe(keys[0]); }
      await tooth.click();
      await expect(inspector.getByTestId("tooth-version")).toContainText("Synthetic tooth saved from UI");
      if (language === "ru" && mobile) {
        await observation.fill("Keep local tooth conflict text");
        const competing = await page.request.post(`${api}/api/medical/tooth-observations/`, { headers: { ...headers, "Idempotency-Key": `tooth-competitor-${id}` },
          data: { ...scope, encounter_id: encounterId, tooth: 11, expected_patient_revision: 1,
            expected_encounter_revision: 1, expected_tooth_revision: 3, observation: "Synthetic competing observation" } });
        expect(competing.status()).toBe(201);
        await inspector.getByRole("button", { name: t("medical.tooth.save"), exact: true }).click();
        await expect(observation).toHaveValue("Keep local tooth conflict text");
        await expect(observation).toHaveAttribute("readonly", "");
        page.once("dialog", dialog => dialog.dismiss());
        await inspector.getByRole("button", { name: t("medical.clinical.reload"), exact: true }).click();
        await expect(observation).toHaveValue("Keep local tooth conflict text");
        page.once("dialog", dialog => dialog.accept());
        await inspector.getByRole("button", { name: t("medical.clinical.reload"), exact: true }).click();
        await expect(inspector).not.toBeVisible();
      } else {
        await observation.fill("Discard synthetic observation");
        await page.keyboard.press("Escape");
        await unsaved.getByRole("button", { name: t("medical.clinical.leaveUnsaved"), exact: true }).click();
      }
      let optionsUnavailable = language === "ru" && !mobile;
      if (optionsUnavailable) await page.route("**/api/medical/tooth-observations/surface-options/**", route => optionsUnavailable
        ? route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ code: "service_unavailable" }) }) : route.continue());
      const surfaceEdits: [string, number][] = [["a", 0], ["a", 1], ["b", 0]];
      if (language === "en" && mobile) surfaceEdits.push(["constructor", 0], ["constructor", 1]);
      for (const [surface, expectedRevision] of surfaceEdits) {
        await tooth.click();
        const editor = inspector.getByTestId("tooth-editor");
        const selector = editor.getByRole("combobox", { name: t("medical.tooth.surface") });
        if (optionsUnavailable) {
          await expect(editor.getByRole("button", { name: t("common.retry"), exact: true })).toBeVisible();
          await expect(selector).toBeDisabled();
          await observation.fill("Whole tooth remains editable during vocabulary outage");
          await expect(editor.getByRole("button", { name: t("medical.tooth.save"), exact: true })).toBeEnabled();
          await observation.fill("");
          optionsUnavailable = false;
          await editor.getByRole("button", { name: t("common.retry"), exact: true }).click();
        }
        await expect(selector).toBeEnabled();
        if (!mobile && surface === "a" && expectedRevision === 0) {
          await selector.focus();
          await page.keyboard.press("ArrowDown");
          await page.keyboard.press("Enter");
          await expect(selector).toBeFocused();
        } else {
          await selector.click();
          await page.getByRole("option", { name: `Synthetic ${surface.toUpperCase()} ${language.toUpperCase()}`, exact: true }).click();
        }
        const text = `Synthetic surface ${surface} revision ${expectedRevision + 1}`;
        await observation.fill(text);
        await expect(selector).toBeDisabled();
        await expect(selector).toHaveAccessibleDescription(t("medical.tooth.surfaceLocked"));
        await expect(selector).toContainText(`Synthetic ${surface.toUpperCase()} ${language.toUpperCase()}`);
        if (surface === "a" && expectedRevision === 0) {
          await editor.screenshot({ path: info.outputPath("surface-editor.png") });
          await page.keyboard.press("Escape");
          await unsaved.getByRole("button", { name: t("medical.clinical.continueEditing"), exact: true }).click();
          await expect(observation).toHaveValue(text);
        }
        const saveResponse = page.waitForResponse(r => r.url().endsWith("/api/medical/tooth-observations/") && r.request().method() === "POST");
        await editor.getByRole("button", { name: t("medical.tooth.save"), exact: true }).click();
        const saved = await saveResponse;
        expect(saved.status()).toBe(201);
        expect(saved.request().postDataJSON()).toMatchObject({ surface, surface_reference: "synthetic-browser-v1", expected_tooth_revision: expectedRevision });
        await expect(inspector).not.toBeVisible();
        await expect(tooth).toBeFocused();
      }
      const snapshot = await page.request.get(`${api}/api/medical/tooth-observations/snapshot/?business_id=1&patient_id=${scope.patient_id}&appointment_id=${id}`, { headers });
      expect(snapshot.status()).toBe(200);
      const positions = (await snapshot.json()).observations;
      expect(positions.find((row: { surface: string }) => row.surface === "a")).toMatchObject({ revision: 2, observation: "Synthetic surface a revision 2" });
      expect(positions.find((row: { surface: string }) => row.surface === "b")).toMatchObject({ revision: 1, observation: "Synthetic surface b revision 1" });
      if (language === "en" && mobile) expect(positions.find((row: { surface: string }) => row.surface === "constructor"))
        .toMatchObject({ revision: 2, observation: "Synthetic surface constructor revision 2" });
      expect(positions.find((row: { surface: string }) => !row.surface)).toMatchObject({ revision: language === "ru" && mobile ? 4 : 3 });
      await chart.getByLabel(t("medical.tooth.asOf"), { exact: true }).fill("2000-01-01T12:00");
      await chart.getByRole("button", { name: t("medical.tooth.show"), exact: true }).click();
      await expect(chart.getByRole("button", { name: `${t("medical.tooth.tooth")} 11: ${t("medical.tooth.empty")}`, exact: true })).toBeVisible();
      let unavailable = language === "ru" && mobile;
      if (unavailable) await page.route("**/api/medical/tooth-observations/snapshot/**", route => unavailable
        ? route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ code: "service_unavailable" }) }) : route.continue());
      await chart.getByRole("button", { name: t("medical.tooth.current"), exact: true }).click();
      if (unavailable) {
        await expect(chart.getByRole("button", { name: t("common.retry"), exact: true })).toBeVisible();
        unavailable = false;
        await chart.getByRole("button", { name: t("common.retry"), exact: true }).click();
      }
      await chart.getByRole("combobox", { name: t("medical.tooth.title") }).click();
      await page.getByRole("option", { name: t("medical.tooth.primary"), exact: true }).click();
      await expect(chart.getByRole("button", { name: `${t("medical.tooth.tooth")} 51: ${t("medical.tooth.empty")}`, exact: true })).toBeVisible();
      await chart.getByRole("combobox", { name: t("medical.tooth.title") }).click();
      await page.getByRole("option", { name: t("medical.tooth.mixed"), exact: true }).click();
      await expect(tooth).toBeVisible();
      await expect(chart.getByRole("button", { name: `${t("medical.tooth.tooth")} 51: ${t("medical.tooth.empty")}`, exact: true })).toBeVisible();
      if (language === "en" && mobile) {
        await chart.getByRole("button", { name: `${t("medical.tooth.tooth")} 51: ${t("medical.tooth.empty")}`, exact: true }).click();
        await inspector.getByLabel(t("medical.tooth.observation"), { exact: true }).fill("First primary tooth observation");
        await inspector.getByRole("button", { name: t("medical.tooth.save"), exact: true }).click();
        await expect(inspector).not.toBeVisible();
        await expect(chart.getByRole("button", { name: `${t("medical.tooth.tooth")} 51: ${t("medical.tooth.observed")}`, exact: true })).toBeVisible();
      }
      if (mobile) {
        await chart.getByRole("combobox", { name: t("medical.tooth.orientation") }).click();
        await page.getByRole("option", { name: t("medical.tooth.q2"), exact: true }).click();
        await expect(chart.getByRole("button", { name: `${t("medical.tooth.tooth")} 61: ${t("medical.tooth.empty")}`, exact: true })).toBeVisible();
      }
      await chart.getByLabel(t("medical.tooth.asOf"), { exact: true }).fill("2000-01-01T12:00");
      await chart.getByRole("button", { name: t("medical.tooth.show"), exact: true }).click();
      const focusTooth = chart.getByRole("button", { name: `${t("medical.tooth.tooth")} ${mobile ? 61 : 51}: ${t("medical.tooth.empty")}`, exact: true });
      await focusTooth.click();
      await expect(inspector.getByText(t("medical.tooth.readOnly"), { exact: true })).toBeVisible();
      await page.keyboard.press("Escape");
      await workspace.screenshot({ path: info.outputPath("chart-mixed.png") });
      await workspace.getByRole("tab", { name: t("medical.clinical.note"), exact: true }).click();
      await expect(complaint).toHaveValue("Retain draft while reading teeth");
      await workspace.getByRole("tab", { name: t("medical.tooth.title"), exact: true }).click();
      await expect(chart.getByLabel(t("medical.tooth.asOf"), { exact: true })).toHaveValue("2000-01-01T12:00");
      await expect(chart.getByRole("combobox", { name: t("medical.tooth.title") })).toContainText(t("medical.tooth.mixed"));
      await expect(focusTooth).toBeFocused();
      await expect(inspector).not.toBeVisible();
      await page.keyboard.press("Escape");
      await page.getByTestId("clinical-unsaved").getByRole("button", { name: t("medical.clinical.leaveUnsaved"), exact: true }).click();
      await expect(workspace).not.toBeVisible();
      await openClinicalWorkspace(page, true);
      await expect(chart.getByLabel(t("medical.tooth.asOf"), { exact: true })).toHaveValue("2000-01-01T12:00");
      await expect(focusTooth).toBeFocused();
      await expect(inspector).not.toBeVisible();
      await workspace.screenshot({ path: info.outputPath("tooth-restored-view.png") });
      await workspace.getByRole("tab", { name: t("medical.clinical.note"), exact: true }).click();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      if (language === "ru" && mobile) {
        try {
          execFileSync(process.env.E2E_PYTHON!, ["e2e/clinical-runtime.py", "revoke", String(id)], { env: process.env, windowsHide: true, stdio: "pipe" });
          await workspace.getByRole("tab", { name: t("medical.tooth.title"), exact: true }).click();
          await expect(workspace.getByText(t("medical.denied"), { exact: true })).toBeVisible();
          await expect(complaint).toHaveCount(0);
          await expect(chart).toHaveCount(0);
        } finally {
          execFileSync(process.env.E2E_PYTHON!, ["e2e/clinical-runtime.py", "restore", String(id)], { env: process.env, windowsHide: true, stdio: "pipe" });
        }
      }
    });
  }
}
