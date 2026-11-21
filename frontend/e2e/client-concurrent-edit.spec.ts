import { expect, test } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";

test.beforeEach(() => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Disposable client fixtures required");
});

for (const [locale, copy] of [["ru", ru], ["kk", kk], ["en", en]] as const) {
  test(`two client editors retain draft and review current values (${locale})`, async ({ page, context }, info) => {
    const session = await crmSession(page);
    const customer = await session.create<{ id: number }>("clients", { full_name: `QA021 ${locale} ${info.project.name}` });
    await page.evaluate(value => localStorage.setItem("ai_smb_language", value), locale);
    const second = await context.newPage();
    for (const editor of [page, second]) {
      await editor.goto(`/app/clients/${customer.id}`);
      await editor.getByRole("button", { name: copy["clients.edit"], exact: true }).click();
      await expect(editor.getByTestId("client-action-form")).toBeVisible();
    }
    const firstForm = page.getByTestId("client-action-form");
    const secondForm = second.getByTestId("client-action-form");
    await firstForm.getByLabel(copy["clients.sourceDetail"], { exact: true }).fill("Source from editor A");
    await secondForm.getByLabel(copy["clients.notes"], { exact: true }).fill("Draft from editor B");
    await firstForm.getByTestId("client-action-submit").click();
    await expect(firstForm).toBeHidden();
    const pending = second.waitForResponse(response => response.request().method() === "PATCH" && response.url().endsWith(`/api/clients/${customer.id}/`));
    await secondForm.getByTestId("client-action-submit").click();
    const rejected = await pending;
    expect(rejected.status()).toBe(409);
    expect(rejected.request().postDataJSON()).not.toHaveProperty("source_detail");
    await expect(secondForm.getByText(copy["clients.editConflictTitle"], { exact: true })).toBeVisible();
    await expect(secondForm.getByLabel(copy["clients.notes"], { exact: true })).toHaveValue("Draft from editor B");
    await expect(secondForm.getByTestId("client-action-submit")).toBeDisabled();
    let stored = await session.read(`clients/${customer.id}`);
    expect(stored.source_detail).toBe("Source from editor A");
    expect(stored.notes).toBe("");

    // A failed review is recoverable without discarding either editor's data.
    const endpoint = `**/api/clients/${customer.id}/`;
    await second.route(endpoint, route => route.request().method() === "GET"
      ? route.fulfill({ status: 503, json: { code: "temporary_service_failure" } }) : route.continue());
    const review = secondForm.getByRole("button", { name: copy["clients.editConflictReview"], exact: true });
    const failedReview = second.waitForResponse(response => response.request().method() === "GET" && response.url().endsWith(`/api/clients/${customer.id}/`) && response.status() === 503);
    await review.click();
    await failedReview;
    await expect(review).toBeEnabled();
    await expect(secondForm.getByLabel(copy["clients.notes"], { exact: true })).toHaveValue("Draft from editor B");
    await second.unroute(endpoint);
    await review.press("Enter");
    await expect(secondForm.getByText("Source from editor A", { exact: true })).toBeVisible();
    await second.screenshot({ path: info.outputPath(`review-${locale}.png`), fullPage: true });
    await secondForm.getByRole("button", { name: copy["clients.editConflictContinue"], exact: true }).scrollIntoViewIfNeeded();
    await second.screenshot({ path: info.outputPath(`review-action-${locale}.png`) });
    expect(await secondForm.evaluate(element => element.scrollWidth <= element.clientWidth + 1)).toBeTruthy();
    await secondForm.getByRole("button", { name: copy["clients.editConflictContinue"], exact: true }).press("Enter");
    await expect(secondForm.getByLabel(copy["clients.name"], { exact: true })).toBeFocused();
    await expect(secondForm.getByLabel(copy["clients.sourceDetail"], { exact: true })).toHaveValue("Source from editor A");
    await expect(secondForm.getByLabel(copy["clients.notes"], { exact: true })).toHaveValue("Draft from editor B");
    await secondForm.getByTestId("client-action-submit").click();
    await expect(secondForm).toBeHidden();
    stored = await session.read(`clients/${customer.id}`);
    expect(stored.source_detail).toBe("Source from editor A");
    expect(stored.notes).toBe("Draft from editor B");
    await second.close();
  });
}
