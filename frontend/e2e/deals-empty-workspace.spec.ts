import { expect, test } from "@playwright/test";
import { spawnSync } from "node:child_process";
import path from "node:path";
import { crmSession } from "./support/crm-workspace";

test("empty deals keep stages, scope pipeline choices and open client creation", async ({ page }, testInfo) => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Disposable database only");
  test.setTimeout(120_000);
  const marker = `empty-${testInfo.project.name}-${Date.now()}`;
  const email = `${marker}@example.invalid`;
  const fixture = spawnSync(process.env.E2E_PYTHON!, ["manage.py", "shell", "-c", `
import json, os
from apps.accounts.models import User
from apps.businesses.models import Business, BusinessMember
from apps.businesses.access import ensure_default_roles
from apps.businesses.capabilities import apply_business_type_defaults
from apps.billing.models import Subscription, SubscriptionPlan
from apps.clients.models import Client
from apps.crm.services import ensure_default_pipeline
assert os.environ.get('ZANI_QUALITY_GATE') == '1'
user = User.objects.create_user(username='${email}', email='${email}', password=os.environ['E2E_PASSWORD'], role='business_owner', full_name='Workspace owner')
pipelines = []
for suffix in ['A', 'B']:
    business = Business.objects.create(owner=user, name=suffix + ' ${marker}', slug='${marker}-' + suffix.lower(), status='active')
    BusinessMember.objects.create(business=business, user=user, role='owner')
    ensure_default_roles(business)
    apply_business_type_defaults(business, configured_by=user)
    pipelines.append(ensure_default_pipeline(business))
    plan = SubscriptionPlan.objects.get(code='growth')
    Subscription.objects.create(business=business, plan=plan, status='active')
Client.objects.create(business=business, full_name='Other business client')
print(json.dumps({'current': pipelines[0].id, 'other': pipelines[1].id}))
`], { cwd: path.resolve(process.cwd(), ".."), env: process.env, encoding: "utf8", timeout: 30_000 });
  expect(fixture.status, fixture.stderr || String(fixture.error || "")).toBe(0);
  const ids = JSON.parse(fixture.stdout.trim().split("\n").at(-1)!) as { current: number; other: number };
  const session = await crmSession(page, email);
  const accessible = await session.list<{ id: number; name: string }>("pipelines");
  expect(accessible).toHaveLength(2);
  expect(accessible[0].name).toBe(accessible[1].name);
  const boardRequests: string[] = [];
  page.on("request", request => {
    const url = new URL(request.url());
    if (url.pathname === "/api/deals/board/") boardRequests.push(url.searchParams.get("pipeline") || "");
  });
  await page.goto(`/app/deals?pipeline=${ids.other}`);
  const workspace = page.getByTestId("deals-workspace-ready");
  await expect(workspace).toBeVisible();
  await expect(page).toHaveURL(new RegExp(`pipeline=${ids.current}(?:&|$)`));
  const board = page.getByTestId("deals-kanban-board");
  await expect(board).toBeVisible();
  await expect(board.locator("section")).toHaveCount(6);
  expect(boardRequests).not.toContain(String(ids.other));
  const pipeline = workspace.getByRole("combobox", { name: "Воронка", exact: true });
  await expect(pipeline).toContainText("Основная воронка");
  await pipeline.click();
  await expect(page.getByRole("option")).toHaveCount(1);
  await page.keyboard.press("Escape");
  await expect(workspace.getByRole("button", { name: "Канбан", exact: true })).toHaveAttribute("aria-pressed", "true");
  await expect(workspace.getByRole("button", { name: "Канбан", exact: true })).toHaveCSS("background-color", "rgb(255, 243, 234)");
  await page.screenshot({ path: testInfo.outputPath("empty-kanban.png"), animations: "disabled" });
  await workspace.getByRole("button", { name: "Таблица", exact: true }).click();
  await expect(board).toBeHidden();
  await expect(workspace.getByText("Сделок не найдено", { exact: true })).toBeVisible();
  await workspace.getByRole("button", { name: "Канбан", exact: true }).click();
  await expect(board).toBeVisible();
  await page.getByRole("button", { name: "Создать сделку", exact: true }).first().click();
  const dealForm = page.getByRole("dialog", { name: "Создать сделку", exact: true });
  await expect(dealForm.getByText("Сначала нужен клиент.", { exact: true })).toBeVisible();
  await expect(dealForm.getByRole("button", { name: "Сохранить", exact: true })).toBeDisabled();
  await page.screenshot({ path: testInfo.outputPath("missing-client-action.png"), animations: "disabled" });
  await dealForm.getByRole("button", { name: "Создать клиента", exact: true }).click();
  await expect(page).toHaveURL(/\/app\/clients\?create=1/);
  const clientForm = page.getByTestId("client-action-form");
  await expect(clientForm).toBeVisible();
  await clientForm.locator('input[name="full_name"]').fill(`First client ${marker}`);
  const saved = page.waitForResponse(response => response.request().method() === "POST" && new URL(response.url()).pathname === "/api/clients/");
  await clientForm.locator('button[type="submit"]').click();
  const response = await saved;
  expect(response.status(), await response.text()).toBe(201);
  const client = await response.json();
  expect(client.business).toBe(session.business);
  await expect(clientForm).toBeHidden();
  await page.goto("/app/deals?create=1");
  await expect(dealForm).toBeVisible();
  await expect(dealForm.getByText("Сначала нужен клиент.", { exact: true })).toBeHidden();
  await dealForm.getByRole("combobox").first().click();
  await expect(page.getByRole("option", { name: `First client ${marker}`, exact: true })).toBeVisible();
  await expect(page.getByRole("option", { name: "Other business client", exact: true })).toHaveCount(0);
  await page.getByRole("option", { name: `First client ${marker}`, exact: true }).click();
  await dealForm.locator('input').first().fill(`First deal ${marker}`);
  const dealSaved = page.waitForResponse(item => item.request().method() === "POST" && new URL(item.url()).pathname === "/api/deals/");
  await dealForm.getByRole("button", { name: "Сохранить", exact: true }).click();
  const dealResponse = await dealSaved;
  expect(dealResponse.status(), await dealResponse.text()).toBe(201);
  const deal = await dealResponse.json();
  expect(deal.business).toBe(session.business);
  expect(deal.pipeline).toBe(ids.current);
  expect(deal.client).toBe(client.id);
  await expect(board.getByText(`First deal ${marker}`, { exact: true })).toBeVisible();
});
