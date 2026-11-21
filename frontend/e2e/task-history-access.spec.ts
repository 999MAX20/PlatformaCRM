import { expect, test } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";
import { ru } from "../src/lib/i18n/ru";

test.beforeEach(() => test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Disposable task fixtures required"));

for (const role of ["operator", "specialist"]) {
  test(`${role} sees own task history through completion and recovery`, async ({ page }, info) => {
    const session = await crmSession(page, `business_${role}@example.com`);
    const task = await session.create<{ id: number }>("tasks", { title: `QA023 ${role}`, assignee: session.userId });
    await page.goto(`/app/tasks/${task.id}`);
    const inspector = page.getByTestId("task-inspector");
    await expect(inspector.getByRole("heading", { name: `QA023 ${role}`, exact: true })).toBeVisible();
    await inspector.getByRole("textbox", { name: ru["taskWorkspace.comment"], exact: true }).fill("QA023 retained comment");
    await inspector.getByRole("button", { name: ru["taskWorkspace.send"], exact: true }).click();
    await expect(inspector.getByRole("textbox", { name: ru["taskWorkspace.comment"], exact: true })).toHaveValue("");
    await inspector.getByRole("button", { name: ru["taskWorkspace.start"], exact: true }).click();
    await expect.poll(async () => (await session.read(`tasks/${task.id}`)).status).toBe("in_progress");
    await inspector.getByRole("tab", { name: ru["taskWorkspace.history"], exact: true }).click();
    await expect(inspector.locator("article")).toHaveCount(3);
    await inspector.getByRole("button", { name: ru["taskWorkspace.complete"], exact: true }).click();
    await expect.poll(async () => (await session.read(`tasks/${task.id}`)).status).toBe("done");
    await expect(inspector.locator("article")).toHaveCount(4);
    await page.reload();
    await inspector.getByRole("tab", { name: ru["taskWorkspace.comments"], exact: true }).click();
    await expect(inspector.getByText("QA023 retained comment", { exact: true })).toBeVisible();
    await page.route("**/api/activity-events/**", route => route.fulfill({ status: 503, json: { detail: "Synthetic read failure" } }));
    await inspector.getByRole("tab", { name: ru["taskWorkspace.history"], exact: true }).click();
    await expect(inspector.getByRole("button", { name: ru["taskWorkspace.refresh"], exact: true })).toBeVisible();
    await page.unroute("**/api/activity-events/**");
    await inspector.getByRole("button", { name: ru["taskWorkspace.refresh"], exact: true }).click();
    await expect(inspector.locator("article")).toHaveCount(4);
    await page.screenshot({ path: info.outputPath(`task-history-${role}.png`), fullPage: true });
  });
}
