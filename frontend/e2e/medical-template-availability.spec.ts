import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";
import { requireIsolatedEnvironment } from "./isolated-environment.mjs";

requireIsolatedEnvironment();
test.use({ actionTimeout: 15_000 });
for (const [language, t] of [["ru", ru], ["kk", kk], ["en", en]] as const) {
  for (const width of [1440, 390]) test(`template availability ${language} ${width}: search pause resume history`, async ({ page }, info) => {
    test.setTimeout(language === "ru" && width === 1440 ? 180_000 : 120_000);
    await page.setViewportSize({ width, height: 900 });
    await page.addInitScript(value => localStorage.setItem("ai_smb_language", value), language);
    await page.goto("/login");
    await page.locator('input[name="email"]').fill("medical-template-head@example.test");
    await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
    const authentication = page.waitForResponse(response => response.url().endsWith("/api/auth/token/") && response.request().method() === "POST");
    await page.locator('form button[type="submit"]').click();
    const token = (await (await authentication).json()).access as string;
    await expect(page).toHaveURL(/\/app\//);
    const command = async (path: string, data: object) => {
      const response = await page.request.post(`${process.env.E2E_API_BASE_URL}/api/medical/document-templates/${path}`, {
        headers: { Authorization: `Bearer ${token}`, "Idempotency-Key": crypto.randomUUID() }, data });
      expect(response.ok(), await response.text()).toBe(true); return response.json();
    };
    const title = `Synthetic availability ${language} ${width}${language === "en" && width === 390 ? " " + "Long".repeat(35) : ""}`;
    const template = await command("common/", { business_id: 1, title, text: "Synthetic text", reason: "",
      metadata: { language, category: "Synthetic category", specialty: "Synthetic specialty", service_ids: [] } });
    await command(`common/versions/${template.version_id}/submit/`, { business_id: 1 });
    await command(`versions/${template.version_id}/decision/`, { business_id: 1, decision: "approved", reason: "" });
    await page.goto("/app/settings#medical-templates");
    const workspace = page.getByTestId("medical-template-workspace");
    if (language === "ru" && width === 1440) {
      const personalTitle = "Synthetic personal search boundary";
      await command("", { business_id: 1, title: personalTitle, text: "Synthetic private draft", reason: "" });
      const filters = workspace.getByRole("form", { name: t["medical.templates.search"], exact: true });
      const input = filters.getByRole("textbox", { name: t["medical.templates.searchText"], exact: true });
      await input.fill(title);
      await input.press("Enter");
      await expect(workspace.getByText(t["medical.templates.noMatches"], { exact: true })).toBeVisible();
      await workspace.getByRole("button", { name: t["medical.templates.common"], exact: true }).click();
      await expect(workspace.getByRole("listitem").filter({ hasText: title })).toBeVisible();
      await workspace.screenshot({ path: info.outputPath("common-search.png") });
      await input.fill(personalTitle);
      await input.press("Enter");
      await expect(workspace.getByText(t["medical.templates.noMatches"], { exact: true })).toBeVisible();
      await workspace.getByRole("button", { name: t["medical.templates.personal"], exact: true }).click();
      await expect(workspace.getByRole("listitem").filter({ hasText: personalTitle })).toBeVisible();
      await workspace.screenshot({ path: info.outputPath("personal-search.png") });
      await filters.getByRole("button", { name: t["medical.templates.resetSearch"], exact: true }).click();
      await expect(input).toHaveValue("");
    }
    await workspace.getByRole("button", { name: t["medical.templates.availability"], exact: true }).click();
    const search = workspace.getByRole("form", { name: t["medical.templates.search"], exact: true });
    const query = search.getByRole("textbox", { name: t["medical.templates.searchText"], exact: true });
    const activity = workspace.getByRole("combobox", { name: t["medical.templates.availability"] });
    await activity.click();
    await workspace.getByRole("option", { name: t["medical.templates.allStatuses"], exact: true }).click();
    await expect(search.getByRole("button", { name: t["medical.templates.search"], exact: true })).toBeEnabled();
    await query.fill("No matching template");
    await query.press("Enter");
    await expect(workspace.getByText(t["medical.templates.noMatches"], { exact: true })).toBeVisible();
    await expect(query).toBeFocused();
    await workspace.screenshot({ path: info.outputPath("search-empty.png") });
    await query.fill(title);
    await search.getByRole("textbox", { name: t["medical.templates.category"], exact: true }).fill("CATEGORY");
    await search.getByRole("textbox", { name: t["medical.templates.specialty"], exact: true }).fill("specialty");
    await search.getByRole("combobox", { name: t["medical.templates.language"] }).click();
    await search.getByRole("option", { name: t[`language.${language}`], exact: true }).click();
    await search.getByRole("button", { name: t["medical.templates.search"], exact: true }).click();
    const row = workspace.getByRole("listitem").filter({ hasText: title });
    await expect(row).toBeVisible();
    await workspace.screenshot({ path: info.outputPath("search-result.png") });
    await row.getByRole("button", { name: t["medical.templates.open"], exact: true }).click();
    const dialog = page.getByRole("dialog");
    const reason = dialog.getByRole("textbox", { name: t["medical.templates.availabilityReason"], exact: true });
    const pause = dialog.getByRole("button", { name: t["medical.templates.pause"], exact: true });
    await expect(pause).toBeDisabled();
    await reason.fill("Synthetic pause reason");
    page.once("dialog", message => message.dismiss());
    await page.keyboard.press("Escape");
    await expect(reason).toHaveValue("Synthetic pause reason");
    let fail = true;
    let releaseSave: (() => void) | undefined;
    const keys: string[] = [];
    await page.route(`**/api/medical/document-templates/${template.id}/availability/`, async route => {
      if (route.request().method() !== "POST") return route.continue();
      keys.push(route.request().headers()["idempotency-key"]);
      if (fail) { fail = false; return route.fulfill({ status: 503, json: { detail: "Synthetic outage" } }); }
      if (language === "ru" && width === 1440 && keys.length === 2) await new Promise<void>(resolve => { releaseSave = resolve; });
      return route.continue();
    });
    await pause.click();
    await expect(dialog.getByRole("alert")).toBeVisible();
    await expect(reason).toHaveValue("Synthetic pause reason");
    await dialog.screenshot({ path: info.outputPath("pause-retry.png") });
    await pause.click();
    if (language === "ru" && width === 1440) {
      await expect.poll(() => Boolean(releaseSave)).toBe(true);
      await page.keyboard.press("Escape");
      await expect(dialog).toBeVisible();
      releaseSave!();
    }
    await expect(dialog).toHaveCount(0);
    expect(keys).toHaveLength(2); expect(keys[0]).toBe(keys[1]);
    await expect(row).toContainText(t["medical.templates.inactive"]);
    await expect(row.getByRole("button")).toBeFocused();
    await activity.click();
    await workspace.getByRole("option", { name: t["medical.templates.inactive"], exact: true }).click();
    await expect(row).toBeVisible();
    await row.getByRole("button").click();
    await expect(dialog.getByText("Synthetic pause reason", { exact: true })).toBeVisible();
    await reason.fill("Synthetic resume reason");
    await dialog.screenshot({ path: info.outputPath("resume-history.png") });
    expect((await new AxeBuilder({ page }).include('[role="dialog"]').withTags(["wcag2a", "wcag2aa"]).analyze()).violations).toEqual([]);
    await dialog.getByRole("button", { name: t["medical.templates.resume"], exact: true }).click();
    await expect(dialog).toHaveCount(0);
    await expect(row).toHaveCount(0);
    await activity.click();
    await workspace.getByRole("option", { name: t["medical.templates.active"], exact: true }).click();
    await expect(row).toContainText(t["medical.templates.active"]);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await search.getByRole("button", { name: t["medical.templates.resetSearch"], exact: true }).click();
    await expect(query).toHaveValue("");
    if (language === "ru" && width === 1440) {
      await row.getByRole("button").click();
      await reason.fill("Synthetic stale input");
      await command(`${template.id}/availability/`, { business_id: 1, is_active: false,
        expected_revision: 2, reason: "Synthetic concurrent change" });
      await pause.click();
      await expect(dialog).toContainText(t["medical.clinical.conflict"]);
      await expect(reason).toHaveValue("Synthetic stale input");
      await dialog.screenshot({ path: info.outputPath("availability-conflict.png") });
      page.once("dialog", message => message.accept());
      await dialog.getByRole("button", { name: t["medical.clinical.reload"], exact: true }).click();
      await expect(dialog).toHaveCount(0);
      for (let revision = 3; revision < 24; revision++) await command(`${template.id}/availability/`, {
        business_id: 1, expected_revision: revision, is_active: revision % 2 === 1, reason: `Synthetic history ${revision}` });
      await workspace.getByRole("button", { name: t["medical.clinical.reload"], exact: true }).click();
      let readFails = true;
      await page.route(`**/api/medical/document-templates/${template.id}/availability/**`, route => {
        if (route.request().method() === "GET" && readFails) return route.fulfill({ status: 503, json: { detail: "Synthetic history outage" } });
        return route.continue();
      });
      await row.getByRole("button").click();
      await expect(dialog.getByRole("alert")).toBeVisible();
      readFails = false;
      await dialog.getByRole("button", { name: t["common.retry"], exact: true }).click();
      await dialog.getByRole("button", { name: t["medical.templates.more"], exact: true }).click();
      await expect(dialog.getByText("Synthetic pause reason", { exact: true })).toBeVisible();
      await dialog.screenshot({ path: info.outputPath("availability-history-page.png") });
      await page.keyboard.press("Escape");
      await expect(dialog).toHaveCount(0);
      await row.getByRole("button").click();
      await reason.fill("Synthetic revoked input");
      await page.route(`**/api/medical/document-templates/${template.id}/availability/`, route =>
        route.request().method() === "POST" ? route.fulfill({ status: 403, json: { detail: "Synthetic access revoked" } }) : route.continue());
      await pause.click();
      await expect(dialog).toHaveCount(0);
      await expect(workspace.getByRole("alert")).toBeVisible();
      await expect(workspace.getByRole("form", { name: t["medical.templates.search"], exact: true })).toHaveCount(0);
      await workspace.screenshot({ path: info.outputPath("availability-denied.png") });
      await workspace.getByRole("button", { name: t["medical.clinical.reload"], exact: true }).click();
      await expect(query).toHaveValue("");
    }
  });
}
