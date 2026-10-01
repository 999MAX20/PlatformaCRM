import { expect, test } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";
import type { PipelineStage } from "../src/types";

test("kanban loads beyond fifty, keeps extra stages in one row, and table pages real results", async ({ page }, testInfo) => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1" || testInfo.project.name !== "desktop-chromium", "Disposable desktop pagination contract");
  test.setTimeout(180_000);
  await page.setViewportSize({ width: 1672, height: 941 });
  const session = await crmSession(page);
  const marker = `Pagination ${Date.now()}`;
  const pipeline = await session.create<{ id: number }>("pipelines", { name: marker, slug: `pagination-${Date.now()}`, is_default: false });
  const stages: PipelineStage[] = [];
  for (let index = 0; index < 8; index++) stages.push(await session.create<PipelineStage>("pipeline-stages", { pipeline: pipeline.id, name: `Stage ${index + 1}`, order: index + 1, probability: 10 }));
  const client = await session.create<{ id: number }>("clients", { full_name: marker });
  const deals: Array<{ id: number; title: string }> = [];
  for (let index = 0; index < 51; index++) deals.push(await session.create("deals", { client: client.id, pipeline: pipeline.id, stage: stages[0].id, title: `${marker} ${String(index).padStart(2, "0")}`, owner: session.userId, amount: "100" }));
  await page.goto(`/app/deals?pipeline=${pipeline.id}`);
  const workspace = page.getByTestId("deals-workspace-ready");
  await expect(workspace).toBeVisible();
  const board = page.getByTestId("deals-kanban-board");
  const stage = page.getByTestId(`deals-kanban-stage-${stages[0].id}`);
  await expect(stage.locator("header")).toContainText("51");
  await expect(stage.locator("article")).toHaveCount(10);
  for (let attempt = 0; attempt < 9 && await stage.locator("article").count() < 51; attempt++) {
    const before = await stage.locator("article").count();
    await stage.getByRole("button", { name: /^\+/ }).click();
    await expect.poll(() => stage.locator("article").count()).toBeGreaterThan(before);
  }
  await expect(stage.locator("article")).toHaveCount(51);
  await expect(stage.getByRole("button", { name: /^\+/ })).toHaveCount(0);
  await expect(stage.getByText(deals[0].title, { exact: true })).toBeVisible();
  const columnTops = await board.locator(":scope > section").evaluateAll((elements) => elements.map((element) => element.getBoundingClientRect().top));
  expect(new Set(columnTops.map(Math.round)).size).toBe(1);
  expect(await board.evaluate((element) => element.scrollWidth > element.clientWidth)).toBe(true);
  await board.evaluate((element) => element.scrollTo({ left: element.scrollWidth, behavior: "instant" }));
  await expect(page.getByTestId(`deals-kanban-stage-${stages[7].id}`)).toBeInViewport();
  await board.evaluate((element) => element.scrollTo({ left: 0, behavior: "instant" }));

  const moved = deals[50];
  await stage.locator("article").filter({ hasText: moved.title }).dragTo(page.getByTestId(`deals-kanban-stage-${stages[1].id}`));
  const nextAction = page.getByRole("dialog", { name: "Следующее действие", exact: true });
  await expect(nextAction).toBeVisible();
  await nextAction.getByRole("button", { name: "Создать задачу", exact: true }).click();
  await expect(nextAction).toBeHidden();
  await expect(stage.locator("article").filter({ hasText: moved.title })).toContainText("Связаться с клиентом");
  await stage.locator("article").filter({ hasText: moved.title }).dragTo(page.getByTestId(`deals-kanban-stage-${stages[1].id}`));
  await expect.poll(async () => (await session.read(`deals/${moved.id}`)).stage).toBe(stages[1].id);
  await expect(page.getByTestId(`deals-kanban-stage-${stages[1].id}`).locator("article")).toHaveCount(1);

  await session.create("deals", { client: client.id, pipeline: pipeline.id, stage: stages[0].id, title: `${marker} unassigned`, owner: null });
  await workspace.getByRole("button", { name: /^Мои\s/ }).click();
  await expect(stage.locator("header")).toContainText("50");

  await workspace.getByRole("button", { name: "Таблица", exact: true }).click();
  await expect(workspace).toBeVisible();
  await expect(workspace.locator("tbody tr")).toHaveCount(20);
  await workspace.locator("tbody tr").first().getByRole("checkbox").check();
  const search = workspace.getByTestId("deals-search-input");
  await search.focus();
  await page.keyboard.press("Delete");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  const footer = workspace.getByTestId("crm-pagination");
  await workspace.locator("thead").getByRole("checkbox").check();
  await footer.getByRole("button", { name: "2", exact: true }).click();
  await expect(workspace.locator("tbody tr")).toHaveCount(20);
  await workspace.locator("thead").getByRole("checkbox").check();
  await expect(workspace.locator('tbody input[type="checkbox"]:checked')).toHaveCount(20);
  await footer.getByRole("button", { name: "3", exact: true }).click();
  await expect(workspace.locator("tbody tr")).toHaveCount(11);
  const direct = await session.read("deals", { pipeline: pipeline.id, status: "open", mine: "true", page_size: 20, page: 3, ordering: "-updated_at" });
  for (const deal of direct.results) await expect(workspace.getByRole("button", { name: deal.title, exact: true })).toBeVisible();
  await page.reload();
  await expect(workspace.getByRole("button", { name: "Таблица", exact: true })).toHaveAttribute("aria-pressed", "true");
});
