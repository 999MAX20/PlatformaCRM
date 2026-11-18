import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { crmSession } from "./support/crm-workspace";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";

test.beforeEach(({ page }) => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Disposable fixtures required");
  test.setTimeout(180_000);
  page.setDefaultTimeout(15_000);
});

for (const [locale, copy] of [["ru", ru], ["kk", kk], ["en", en]] as const) {
  test(`payments modal preserves history and keyboard navigation (${locale})`, async ({ page }, info) => {
    const s = await crmSession(page);
    const client = await s.create<{ id: number }>("clients", { full_name: `Payments ${locale} ${info.project.name} ${Date.now()}` });
    const payment = await s.create<{ id: number }>("client-payments", {
      client: client.id, amount: "1250.50", currency: "KZT", method: "cash",
      occurred_at: "2026-10-01T10:00:00Z", note: "Payment history acceptance",
      submission_id: crypto.randomUUID(),
    });
    await page.evaluate(value => localStorage.setItem("ai_smb_language", value), locale);
    await page.goto("/app/clients");
    await expect(page.getByTestId("clients-workspace-ready")).toBeVisible();
    await expect(page.getByTestId("crm-pagination")).toHaveCount(0);
    const opener = page.locator('[data-focus-return-id="clients-payments"]').filter({ visible: true });
    await expect(opener).toHaveText(copy["payments.title"]);
    expect(await opener.innerText()).toBe(copy["payments.title"]);
    await expect(opener.locator("button, svg")).toHaveCount(0);
    await opener.press("Enter");
    const journal = page.getByTestId("payments-journal");
    await expect(journal.getByRole("heading", { name: copy["payments.title"], exact: true })).toBeVisible();
    const row = journal.getByTestId(`payment-row-${payment.id}`);
    await expect(row).toContainText("1250.50 KZT");
    await expect(row).toContainText("Payment history acceptance");
    for (const key of ["date", "method", "source", "actor"]) await expect(row.getByText(copy[`payments.${key}`], { exact: true })).toBeVisible();
    const bounds = await journal.boundingBox();
    expect(Math.abs(bounds!.x + bounds!.width / 2 - page.viewportSize()!.width / 2)).toBeLessThan(2);
    await journal.evaluate(async el => { await Promise.all(el.getAnimations({ subtree: true }).filter(a => a.effect?.getTiming().iterations !== Infinity).map(a => a.finished.catch(() => undefined))); });
    expect((await new AxeBuilder({ page }).include('[data-testid="payments-journal"]').withTags(["wcag2a", "wcag2aa"]).analyze()).violations).toEqual([]);
    await page.screenshot({ path: info.outputPath(`payments-${locale}.png`) });
    await journal.getByTestId("payment-add").click();
    const form = page.getByTestId("payment-form");
    await expect(form).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(form).toBeHidden();
    await expect(journal.getByTestId("payment-add")).toBeFocused();
    await journal.getByLabel(copy["payments.search"], { exact: true }).fill("no-match-payment-acceptance");
    await expect(journal.getByText(copy["payments.empty"], { exact: true })).toBeVisible();
    if (locale === "en") {
      await page.evaluate(() => { document.documentElement.style.fontSize = "200%"; });
      await journal.getByRole("button", { name: copy["payments.next"], exact: true }).scrollIntoViewIfNeeded();
      expect(await journal.evaluate(el => el.scrollWidth - el.clientWidth)).toBeLessThanOrEqual(1);
      expect(await journal.locator(":scope > div.overflow-auto").evaluate(el => el.scrollWidth - el.clientWidth)).toBeLessThanOrEqual(1);
      await page.screenshot({ path: info.outputPath("payments-text200.png") });
      await journal.getByText(copy["payments.empty"], { exact: true }).scrollIntoViewIfNeeded();
      await page.screenshot({ path: info.outputPath("payments-text200-content.png") });
      await page.evaluate(() => { document.documentElement.style.fontSize = ""; });
    }
    await page.keyboard.press("Escape");
    await expect(journal).toBeHidden();
    await expect(opener).toBeFocused();
  });
}

test("payment modal retries reads and records receipt/refund through existing forms", async ({ page }, info) => {
  const s = await crmSession(page);
  const name = `Payment workflow ${info.project.name} ${Date.now()}`;
  const client = await s.create<{ id: number }>("clients", { full_name: name });
  await page.goto(`/app/clients/${client.id}`);
  await page.route("**/api/client-payments/?**", route => route.fulfill({ status: 503, json: { detail: "Isolated read failure" } }));
  await page.getByTestId("client-payments-open").click();
  const journal = page.getByTestId("payments-journal");
  await expect(journal.getByRole("button", { name: ru["common.retry"], exact: true })).toBeVisible({ timeout: 30_000 });
  await page.unroute("**/api/client-payments/?**");
  await journal.getByRole("button", { name: ru["common.retry"], exact: true }).click();
  await expect(journal.getByText(ru["payments.empty"], { exact: true })).toBeVisible();
  await journal.getByTestId("payment-add").click();
  const form = page.getByTestId("payment-form");
  await expect(form.getByLabel(ru["payments.client"], { exact: true })).toHaveValue(name);
  await form.getByLabel(/^Сумма/).fill("1250.50");
  await form.getByLabel(/^Дата/).fill("2026-10-01T10:00");
  await form.getByLabel(ru["payments.note"], { exact: true }).fill("Receipt retained in modal history");
  const receiptResponse = page.waitForResponse(r => r.request().method() === "POST" && r.url().endsWith("/api/client-payments/"));
  await form.locator('button[type="submit"]').click();
  const receiptResult = await receiptResponse;
  expect(receiptResult.status(), await receiptResult.text()).toBe(201);
  const receipt = await receiptResult.json();
  const row = journal.getByTestId(`payment-row-${receipt.id}`);
  await expect(row).toContainText("1250.50 KZT");
  await row.getByRole("button", { name: ru["payments.refund"], exact: true }).click();
  await form.getByLabel(/^Сумма/).fill("250.50");
  await form.getByLabel(ru["payments.reason"], { exact: true }).fill("Isolated refund acceptance");
  const refundResponse = page.waitForResponse(r => r.request().method() === "POST" && r.url().endsWith("/api/client-payments/"));
  await form.locator('button[type="submit"]').click();
  const refundResult = await refundResponse;
  expect(refundResult.status(), await refundResult.text()).toBe(201);
  const refund = await refundResult.json();
  await expect(journal.getByTestId(`payment-row-${refund.id}`)).toContainText("Isolated refund acceptance");
  expect(await s.read(`client-payments/${receipt.id}`, { business: s.business })).toMatchObject({ refunded_amount: "250.50", remaining_amount: "1000.00" });
  await journal.getByRole("combobox", { name: new RegExp(`^${ru["payments.kind"]}`) }).click();
  await page.getByRole("option", { name: ru["payments.refundKind"], exact: true }).click();
  await expect(row).toHaveCount(0);
  await expect(journal.getByTestId(`payment-row-${refund.id}`)).toBeVisible();
  await page.screenshot({ path: info.outputPath("refund-history.png") });
  await page.keyboard.press("Escape");
  await expect(page.getByTestId("client-payments-open")).toBeFocused();
});
