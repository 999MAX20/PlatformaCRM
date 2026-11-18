import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { crmSession } from "./support/crm-workspace";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";

test.beforeEach(({ page }) => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Disposable fixtures required");
  test.setTimeout(180_000);
  page.setDefaultTimeout(30_000);
});

for (const [locale, copy] of [["ru", ru], ["kk", kk], ["en", en]] as const) {
  test(`payments page preserves history and keyboard navigation (${locale})`, async ({ page }, info) => {
    const s = await crmSession(page);
    const name = `Payments ${locale} ${info.project.name} ${Date.now()}`;
    const client = await s.create<{ id: number }>("clients", { full_name: name });
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
    await expect(page).toHaveURL(/\/app\/payments$/);
    await expect(page.getByRole("dialog")).toHaveCount(0);
    await expect(page.getByRole("heading", { name: copy["payments.title"], exact: true })).toBeVisible();
    await journal.getByLabel(copy["payments.search"], { exact: true }).fill(name);
    const row = journal.getByTestId(`payment-row-${payment.id}`);
    await expect(row).toContainText("1250.50 KZT");
    await expect(row).toContainText("Payment history acceptance");
    for (const key of ["date", "method", "source", "actor"]) await expect(row.getByText(copy[`payments.${key}`], { exact: true })).toBeVisible();
    if (info.project.name === "desktop") {
      const search = await journal.getByLabel(copy["payments.search"], { exact: true }).boundingBox();
      const add = await journal.getByTestId("payment-add").boundingBox();
      expect(Math.abs(search!.y + search!.height - add!.y - add!.height)).toBeLessThan(2);
      expect(search!.width).toBeLessThan(300);
    }
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
      await journal.getByTestId("payment-add").scrollIntoViewIfNeeded();
      expect(await journal.evaluate(el => el.scrollWidth - el.clientWidth)).toBeLessThanOrEqual(1);

      await page.screenshot({ path: info.outputPath("payments-text200.png") });
      await journal.getByText(copy["payments.empty"], { exact: true }).scrollIntoViewIfNeeded();
      await page.screenshot({ path: info.outputPath("payments-text200-content.png") });
      await page.evaluate(() => { document.documentElement.style.fontSize = ""; });
    }
    await page.goBack();
    await expect(page.getByTestId("clients-workspace-ready")).toBeVisible();
  });
}

test("payment page retries reads and records receipt/refund through existing forms", async ({ page }, info) => {
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
  await form.getByLabel(ru["payments.note"], { exact: true }).fill("Receipt retained in page history");
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
  await page.reload();
  await expect(page).toHaveURL(new RegExp(`/app/payments\\?client=${client.id}$`));
  await expect(page.getByTestId(`payment-row-${refund.id}`)).toBeVisible();
});

test("scroll loads older history, retries next page and resets filters", async ({ page }, info) => {
  const s = await crmSession(page);
  const client = await s.create<{ id: number }>("clients", { full_name: `Long history ${info.project.name} ${Date.now()}` });
  const ids: number[] = [];
  for (let i = 0; i < 22; i++) {
    const payment = await s.create<{ id: number }>("client-payments", { client: client.id, amount: "10.00", currency: "KZT", method: "cash", occurred_at: `2026-10-01T10:${String(i).padStart(2, "0")}:00Z`, note: `History ${i}`, submission_id: crypto.randomUUID() });
    ids.push(payment.id);
  }
  await page.goto(`/app/payments?client=${client.id}`);
  const rows = page.locator('[data-testid^="payment-row-"]');
  await expect(rows).toHaveCount(20);
  await page.route("**/api/client-payments/?**", route => new URL(route.request().url()).searchParams.get("page") === "2" ? route.fulfill({ status: 503, json: { detail: "Next page unavailable" } }) : route.continue());
  await rows.last().scrollIntoViewIfNeeded();
  await expect(page.getByRole("button", { name: ru["common.retry"], exact: true })).toBeVisible({ timeout: 30000 });
  await expect(rows).toHaveCount(20);
  await page.unroute("**/api/client-payments/?**");
  await page.getByRole("button", { name: ru["common.retry"], exact: true }).click();
  await expect(rows).toHaveCount(22);
  await expect(page.getByTestId(`payment-row-${ids[0]}`)).toBeVisible();
  await expect(page.getByRole("navigation", { name: ru["payments.pagination"] })).toHaveCount(0);
  await page.getByLabel(ru["payments.search"], { exact: true }).fill("missing-history");
  await expect(rows).toHaveCount(0);
  await expect(page.getByText(ru["payments.empty"], { exact: true })).toBeVisible();
  await page.getByLabel(ru["payments.search"], { exact: true }).fill("");
  await expect(rows).toHaveCount(22);
  await page.goto("/app/payments?client=invalid");
  await expect(page.getByTestId("payment-add")).toHaveCount(0);
  await expect(rows).toHaveCount(0);
});

test("payment draft survives cancelled navigation", async ({ page }) => {
  const s = await crmSession(page);
  const client = await s.create<{ id: number }>("clients", { full_name: `Draft ${Date.now()}` });
  await page.goto(`/app/clients/${client.id}`);
  await page.getByTestId("client-payments-open").click();
  await page.getByTestId("payment-add").click();
  const form = page.getByTestId("payment-form");
  await form.getByLabel(/^Сумма/).fill("123.45");
  await page.goBack();
  const confirmation = page.getByRole("dialog").filter({ has: page.getByRole("heading", { name: ru["payments.discardTitle"], exact: true }) });
  await expect(confirmation).toBeVisible();
  await confirmation.getByRole("button", { name: ru["common.cancel"], exact: true }).click();
  await expect(form.getByLabel(/^Сумма/)).toHaveValue("123.45");
  await page.goBack();
  await confirmation.getByRole("button", { name: ru["payments.discard"], exact: true }).filter({ hasText: ru["payments.discard"] }).click();
  await expect(page).toHaveURL(new RegExp(`/app/clients/${client.id}$`));
});

test("payments route denies users without payment permission", async ({ page }) => {
  await crmSession(page, "business_specialist@example.com");
  await page.goto("/app/payments");
  await expect(page.getByTestId("forbidden-state")).toBeVisible();
  await expect(page.getByTestId("payment-add")).toHaveCount(0);
  await expect(page.locator('[data-testid^="payment-row-"]')).toHaveCount(0);
});
