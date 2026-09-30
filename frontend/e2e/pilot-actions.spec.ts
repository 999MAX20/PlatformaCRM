import { expect, test, type Page } from "@playwright/test";

const api = process.env.E2E_API_BASE_URL || "http://127.0.0.1:8000";

async function ownerSession(page: Page) {
  await page.goto("/login");
  await page.locator('form input[type="email"]').fill(process.env.E2E_OWNER_EMAIL || "business_owner@example.com");
  await page.locator('form input[type="password"]').fill(process.env.E2E_PASSWORD || "ZaniTest123!");
  const loggedIn = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/api/auth/token/"));
  await page.locator('form button[type="submit"]').click();
  const response = await loggedIn;
  expect(response.ok()).toBeTruthy();
  const headers = { Authorization: `Bearer ${(await response.json()).access}` };
  const me = await page.request.get(`${api}/api/auth/me/`, { headers });
  expect(me.ok()).toBeTruthy();
  const profile = await me.json();
  await expect(page).toHaveURL(/\/app/);
  return {
    headers, business: profile.businesses[0].id, userId: profile.id,
    async create(resource: string, data: Record<string, unknown>) {
      const created = await page.request.post(`${api}/api/${resource}/`, { headers, data: { business: profile.businesses[0].id, ...data } });
      expect(created.status(), await created.text()).toBe(201);
      return created.json();
    },
    async read(resource: string, id: number) {
      const read = await page.request.get(`${api}/api/${resource}/${id}/`, { headers });
      expect(read.ok()).toBeTruthy();
      return read.json();
    },
  };
}

async function mutate(page: Page, suffix: string, act: () => Promise<void>) {
  const pending = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith(suffix));
  await act();
  const response = await pending;
  expect(response.ok(), await response.text()).toBeTruthy();
  return response.json();
}

test("task workspace persists lifecycle, assignment, watch, due dates and comment actions", async ({ page }) => {
  test.setTimeout(120_000);
  const session = await ownerSession(page);
  const task = await session.create("tasks", { title: `Pilot task actions ${Date.now()}` });
  await page.goto(`/app/tasks/${task.id}`);
  const clickAction = (id: string) => page.locator(`[data-task-action-id="${id}"]`).click();
  await mutate(page, `/api/tasks/${task.id}/start/`, () => clickAction("start"));
  expect((await session.read("tasks", task.id)).status).toBe("in_progress");
  await mutate(page, `/api/tasks/${task.id}/assign-to-me/`, () => page.getByRole("button", { name: "Назначить на меня", exact: true }).click());
  const assigned = await session.read("tasks", task.id);
  expect(assigned.assignee).toBeTruthy();
  await mutate(page, `/api/tasks/${task.id}/add-watcher/`, () => page.getByRole("button", { name: "Наблюдать", exact: true }).click());
  expect((await session.read("tasks", task.id)).watchers).toContain(assigned.assignee);
  await mutate(page, `/api/tasks/${task.id}/due-today/`, () => page.getByRole("button", { name: "сегодня", exact: true }).click());
  const today = await session.read("tasks", task.id);
  expect(today.reminder_at).toBeTruthy();
  await mutate(page, `/api/tasks/${task.id}/due-tomorrow/`, () => page.getByRole("button", { name: "Завтра", exact: true }).click());
  const tomorrow = await session.read("tasks", task.id);
  expect(new Date(tomorrow.due_at).getTime()).toBeGreaterThan(new Date(today.due_at).getTime());
  await page.locator("textarea").fill("Pilot comment retained after reload");
  const comment = await mutate(page, `/api/tasks/${task.id}/add-comment/`, () => page.locator('form button[type="submit"]').click());
  await page.reload();
  await expect(page.getByText(comment.text, { exact: true })).toBeVisible();
  const deleted = page.waitForResponse(response => response.request().method() === "DELETE" && response.url().endsWith(`/api/tasks/${task.id}/comments/${comment.id}/`));
  await page.getByRole("button", { name: "Удалить комментарий", exact: true }).click();
  expect((await deleted).status()).toBe(204);
  await expect(page.getByText(comment.text, { exact: true })).not.toBeVisible();
  await clickAction("cancel");
  const confirmation = page.getByRole("dialog");
  await expect(confirmation.getByRole("button", { name: "Отменить", exact: true })).toBeDisabled();
  await confirmation.locator("textarea").fill("Client asked to postpone");
  await mutate(page, `/api/tasks/${task.id}/cancel/`, () => confirmation.getByRole("button", { name: "Отменить", exact: true }).click());
  expect((await session.read("tasks", task.id)).cancel_reason).toBe("Client asked to postpone");
  await mutate(page, `/api/tasks/${task.id}/reopen/`, () => clickAction("reopen"));
  expect((await session.read("tasks", task.id)).status).toBe("open");
  await mutate(page, `/api/tasks/${task.id}/complete/`, () => clickAction("complete"));
  await page.reload();
  expect((await session.read("tasks", task.id)).status).toBe("done");
  await expect(page.locator('[data-task-action-id="reopen"]')).toBeVisible();
});

test("lead and deal terminal actions preserve reasons, reopen and independent persisted state", async ({ page }) => {
  test.setTimeout(120_000);
  const session = await ownerSession(page);
  const client = await session.create("clients", { full_name: `Terminal client ${Date.now()}` });
  const lead = await session.create("leads", { client: client.id, source: "manual", message: "Pilot lifecycle", status: "new" });
  await page.goto(`/app/leads/${lead.id}`);
  async function crmAction(id: string, suffix: string, reason?: string) {
    return mutate(page, suffix, async () => {
      await page.locator(`[data-crm-action-id="${id}"]`).click();
      const dialog = page.getByRole("dialog");
      if (reason) {
        await expect(dialog.locator('button[type="submit"]')).toBeDisabled();
        await dialog.locator("textarea").fill(reason);
        await dialog.locator('button[type="submit"]').click();
      } else if (await dialog.isVisible()) {
        await dialog.getByRole("button", { name: "Подтвердить", exact: true }).click();
      }
    });
  }
  await crmAction("take", `/api/leads/${lead.id}/take-in-work/`);
  await crmAction("contacted", `/api/leads/${lead.id}/mark-contacted/`);
  await crmAction("lost", `/api/leads/${lead.id}/mark-lost/`, "Lead declined appointment");
  expect((await session.read("leads", lead.id)).lost_reason).toBe("Lead declined appointment");
  await crmAction("reopen", `/api/leads/${lead.id}/reopen/`);
  const deal = await crmAction("create_deal", `/api/leads/${lead.id}/create-deal/`);
  await page.goto(`/app/deals/${deal.id}`);
  await crmAction("lost", `/api/deals/${deal.id}/mark-lost/`, "Deal declined offer");
  expect((await session.read("deals", deal.id)).lost_reason).toBe("Deal declined offer");
  await crmAction("reopen", `/api/deals/${deal.id}/reopen/`);
  await crmAction("won", `/api/deals/${deal.id}/mark-won/`);
  await page.reload();
  expect((await session.read("deals", deal.id)).status).toBe("won");
  await expect(page.locator('[data-crm-action-id="reopen"]')).toBeVisible();
});

test("waiting automation can be cancelled from its actual run row", async ({ page }) => {
  test.setTimeout(90_000);
  const session = await ownerSession(page);
  const created = await page.request.post(`${api}/api/automation-rules/create-manual/`, {
    headers: session.headers,
    data: {
      business: session.business, name: `Pilot WAIT cancellation ${Date.now()}`,
      trigger_type: "lead_created", is_active: true, conditions: [],
      actions: [{ action_type: "wait", config: {}, delay_seconds: 3600 }],
    },
  });
  expect(created.status(), await created.text()).toBe(201);
  const rule = await created.json();
  const client = await session.create("clients", { full_name: `Wait client ${Date.now()}` });
  const lead = await session.create("leads", { client: client.id, source: "manual", message: "Wait fixture" });
  // Keep this fixture from creating additional runs for later viewport scenarios.
  const disabled = await page.request.patch(`${api}/api/automation-rules/${rule.id}/`, {
    headers: session.headers, data: { is_active: false },
  });
  expect(disabled.ok()).toBeTruthy();
  const response = await page.request.get(`${api}/api/automation-runs/`, { headers: session.headers });
  expect(response.ok()).toBeTruthy();
  const payload = await response.json();
  const run = (payload.results || payload).find((item: { rule: number }) => item.rule === rule.id);
  expect(run?.status).toBe("waiting");
  await page.goto("/app/automations");
  const row = page.locator("div.grid").filter({ has: page.locator("p").filter({ hasText: new RegExp(`^Lead #${lead.id} ·`) }) }).last();
  await expect(row.getByText("Ожидает", { exact: true })).toBeVisible();
  await expect(row.getByRole("button", { name: "Отменить запуск", exact: true })).toBeVisible();
  await mutate(page, `/api/automation-runs/${run.id}/cancel/`, () => row.getByRole("button", { name: "Отменить запуск", exact: true }).click());
  expect((await session.read("automation-runs", run.id)).status).toBe("cancelled");
  await page.reload();
  expect((await session.read("automation-runs", run.id)).status).toBe("cancelled");
  await expect(row.getByRole("button", { name: "Отменить запуск", exact: true })).toHaveCount(0);
  const enabled = await page.request.patch(`${api}/api/automation-rules/${rule.id}/`, {
    headers: session.headers, data: { is_active: true },
  });
  expect(enabled.ok()).toBeTruthy();
  try {
    await mutate(page, `/api/automation-runs/${run.id}/retry/`, () => row.getByRole("button", { name: "Повторить", exact: true }).click());
    await expect.poll(async () => (await session.read("automation-runs", run.id)).status).toBe("success");
    await page.reload();
    await expect(row.getByRole("button", { name: "Повторить", exact: true })).toHaveCount(0);
    const readRuns = await page.request.get(`${api}/api/automation-runs/`, { headers: session.headers });
    const current = await readRuns.json();
    expect((current.results || current).filter((item: { rule: number }) => item.rule === rule.id)).toHaveLength(1);
  } finally {
    await page.request.patch(`${api}/api/automation-rules/${rule.id}/`, {
      headers: session.headers, data: { is_active: false },
    });
  }
});

test("account profile and task notification preferences survive reload", async ({ page }) => {
  const session = await ownerSession(page);
  await page.goto("/app/account");
  const nameInput = page.getByLabel("Имя", { exact: true });
  const originalName = await nameInput.inputValue();
  const newName = `Pilot profile ${Date.now()}`;
  await nameInput.fill(newName);
  const saved = page.waitForResponse(response => response.request().method() === "PATCH" && response.url().endsWith("/api/auth/me/"));
  await page.locator("#profile").getByRole("button", { name: "Сохранить", exact: true }).click();
  expect((await saved).ok()).toBeTruthy();
  await page.reload();
  await expect(nameInput).toHaveValue(newName);
  const category = page.getByRole("switch", { name: "Задачи", exact: true });
  for (const enabled of [false, true]) {
    const changed = page.waitForResponse(response => ["POST", "PATCH"].includes(response.request().method()) && response.url().includes("/api/notification-preferences/"));
    await category.click();
    const result = await changed;
    expect(result.ok()).toBeTruthy();
    expect((await result.json()).in_app_enabled).toBe(enabled);
    await page.reload();
  }
  const restore = await page.request.patch(`${api}/api/auth/me/`, { headers: session.headers, data: { full_name: originalName } });
  expect(restore.ok()).toBeTruthy();
});

test("working-hours deep link returns focus to a resource beyond the first page", async ({ page }) => {
  test.setTimeout(90_000);
  const session = await ownerSession(page);
  const unique = Date.now();
  for (let index = 0; index < 21; index += 1) {
    await session.create("resources", { name: `ZZ paging ${unique} ${String(index).padStart(2, "0")}`, resource_type: "staff", is_active: true });
  }
  const target = await session.create("resources", { name: `ZZZ last resource ${unique}`, resource_type: "staff", is_active: true });
  await page.goto(`/app/business/working-hours?view=resources&resource=${target.id}`);
  const editor = page.getByTestId("working-hours-edit-modal");
  await expect(editor).toBeVisible();
  await editor.getByRole("button", { name: /^(Закрыть|Close|Жабу)$/ }).click();
  const row = page.locator(`[data-focus-return-id="working-hours-resource-${target.id}"]:visible`).first();
  await expect(row).toBeFocused();
  await row.press("Enter");
  await expect(editor).toBeVisible();
  await expect(editor.locator(":focus")).toHaveCount(1);
});

test("resource edits and deactivate-reactivate preserve the same specialist", async ({ page }) => {
  const session = await ownerSession(page);
  const resource = await session.create("resources", { name: `Pilot specialist ${Date.now()}`, resource_type: "staff", is_active: true });
  const renamed = `${resource.name} edited`;
  await page.goto(`/app/business/resources?resource=${resource.id}`);
  const editor = page.getByTestId("resource-edit-modal");
  await editor.getByLabel("Название", { exact: true }).fill(renamed);
  const save = page.waitForResponse(response => response.request().method() === "PATCH" && response.url().endsWith(`/api/resources/${resource.id}/`));
  await editor.locator('button[type="submit"]').click();
  expect((await save).ok()).toBeTruthy();
  expect((await session.read("resources", resource.id)).name).toBe(renamed);
  await page.goto(`/app/business/resources?search=${encodeURIComponent(renamed)}`);
  for (const active of [false, true]) {
    await page.getByRole("button", { name: `Действия с ресурсом «${renamed}»`, exact: true }).click();
    const label = active ? "Активировать" : "Деактивировать";
    const changed = page.waitForResponse(response => response.request().method() === "PATCH" && response.url().endsWith(`/api/resources/${resource.id}/`));
    await page.getByRole("menuitem", { name: label, exact: true }).click();
    if (!active) await page.getByRole("dialog").getByRole("button", { name: label, exact: true }).click();
    expect((await changed).ok()).toBeTruthy();
    await page.reload();
    const persisted = await session.read("resources", resource.id);
    expect(persisted.is_active).toBe(active);
    expect(persisted.name).toBe(renamed);
    expect(persisted.resource_type).toBe("staff");
  }
});

test("automation template creates a persisted draft and toggles without running effects", async ({ page }) => {
  const session = await ownerSession(page);
  const beforeRuns = await page.request.get(`${api}/api/automation-runs/`, { headers: session.headers });
  expect(beforeRuns.ok()).toBeTruthy();
  const beforeCount = (await beforeRuns.json()).count;
  await page.goto("/app/automations");
  const created = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/api/automation-rules/apply-template/"));
  await page.getByRole("button", { name: "Добавить черновик", exact: true }).first().click();
  const response = await created;
  expect(response.status()).toBe(201);
  const rule = await response.json();
  expect((await session.read("automation-rules", rule.id)).is_active).toBe(false);
  const card = page.getByRole("heading", { name: rule.name, level: 2, exact: true }).locator("..");
  for (const active of [true, false]) {
    const updated = page.waitForResponse(item => item.request().method() === "PATCH" && item.url().endsWith(`/api/automation-rules/${rule.id}/`));
    await card.getByRole("button", { name: active ? "Включить" : "Отключить", exact: true }).click();
    expect((await updated).ok()).toBeTruthy();
    await page.reload();
    expect((await session.read("automation-rules", rule.id)).is_active).toBe(active);
  }
  const afterRuns = await page.request.get(`${api}/api/automation-runs/`, { headers: session.headers });
  expect(afterRuns.ok()).toBeTruthy();
  expect((await afterRuns.json()).count).toBe(beforeCount);
  // Only this disposable fixture is removed; no trigger was emitted for its rule.
  const removed = await page.request.delete(`${api}/api/automation-rules/${rule.id}/`, { headers: session.headers });
  expect(removed.status()).toBe(204);
});

for (const kind of ["resources", "services"] as const) {
  test(`${kind} editor deep link works outside the visible list and preserves its filter`, async ({ page }) => {
    const session = await ownerSession(page);
    const item = await session.create(kind, kind === "resources"
      ? { name: `Deep specialist ${Date.now()}`, resource_type: "staff", is_active: true }
      : { name: `Deep service ${Date.now()}`, duration_minutes: 30, price_from: "1000.00" });
    const key = kind === "resources" ? "resource" : "service";
    const search = `No-match-${Date.now()}`;
    await page.goto(`/app/business/${kind}?${key}=${item.id}&search=${search}`);
    const editor = page.getByTestId(`${key}-edit-modal`);
    await expect(editor).toBeVisible();
    await expect(editor.getByLabel("Название", { exact: true })).toHaveValue(item.name);
    const updatedName = `${item.name} edited`;
    await editor.getByLabel("Название", { exact: true }).fill(updatedName);
    const saved = page.waitForResponse(response => response.request().method() === "PATCH" && response.url().endsWith(`/api/${kind}/${item.id}/`));
    await editor.locator('button[type="submit"]').click();
    expect((await saved).ok()).toBeTruthy();
    expect((await session.read(kind, item.id)).name).toBe(updatedName);
    await page.reload();
    await expect(editor.getByLabel("Название", { exact: true })).toHaveValue(updatedName);
    await editor.getByRole("button", { name: "Закрыть", exact: true }).click();
    await expect(editor).not.toBeVisible();
    expect(new URL(page.url()).searchParams.get("search")).toBe(search);
    expect(new URL(page.url()).searchParams.has(key)).toBe(false);
  });
}

test("setup editor deep links reject another company's resource and service", async ({ page, request }) => {
  await ownerSession(page);
  const login = await request.post(`${api}/api/auth/token/`, { data: {
    email: process.env.E2E_FOREIGN_OWNER_EMAIL || "foreign_owner@example.com",
    password: process.env.E2E_PASSWORD || "ZaniTest123!",
  } });
  expect(login.ok()).toBeTruthy();
  const headers = { Authorization: `Bearer ${(await login.json()).access}` };
  const me = await (await request.get(`${api}/api/auth/me/`, { headers })).json();
  for (const kind of ["resources", "services"]) {
    const name = `Foreign setup ${kind} ${Date.now()}`;
    const response = await request.post(`${api}/api/${kind}/`, { headers, data: {
      business: me.businesses[0].id, name,
      ...(kind === "resources" ? { resource_type: "staff" } : { duration_minutes: 30, price_from: "1000.00" }),
    } });
    expect(response.status()).toBe(201);
    const item = await response.json();
    const key = kind === "resources" ? "resource" : "service";
    const denied = page.waitForResponse(result => result.request().method() === "GET" && result.url().endsWith(`/api/${kind}/${item.id}/`));
    await page.goto(`/app/business/${kind}?${key}=${item.id}`);
    expect([403, 404]).toContain((await denied).status());
    await expect(page.getByTestId(`${key}-edit-modal`)).not.toBeVisible();
    await expect(page.locator("main")).not.toContainText(name);
  }
});

test("manual automation preview creates no effects and saves the reviewed draft", async ({ page }) => {
  const session = await ownerSession(page);
  async function count(resource: string) {
    const response = await page.request.get(`${api}/api/${resource}/`, { headers: session.headers });
    expect(response.ok()).toBeTruthy();
    return (await response.json()).count;
  }
  const tasksBefore = await count("tasks");
  const runsBefore = await count("automation-runs");
  const rulesBefore = await count("automation-rules");
  const name = `Pilot reviewed rule ${Date.now()}`;
  await page.goto("/app/automations");
  await page.locator("summary").filter({ hasText: "Расширенная настройка" }).click();
  await page.getByRole("button", { name: "Расширенный конструктор", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Название", { exact: true }).fill(name);
  const previewed = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/api/automation-rules/preview/"));
  await dialog.getByRole("button", { name: "Проверить правило", exact: true }).click();
  const preview = await previewed;
  expect(preview.ok()).toBeTruthy();
  expect((await preview.json()).actions_count).toBe(1);
  expect(await count("automation-rules")).toBe(rulesBefore);
  expect(await count("tasks")).toBe(tasksBefore);
  expect(await count("automation-runs")).toBe(runsBefore);
  const saved = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/api/automation-rules/create-manual/"));
  await dialog.getByRole("button", { name: "Сохранить правило", exact: true }).click();
  const response = await saved;
  expect(response.status()).toBe(201);
  const rule = await response.json();
  await page.reload();
  expect(await session.read("automation-rules", rule.id)).toMatchObject({ name, is_active: false });
  expect(await count("tasks")).toBe(tasksBefore);
  expect(await count("automation-runs")).toBe(runsBefore);
});

test("business profile save persists after reload and can restore the original value", async ({ page }) => {
  const session = await ownerSession(page);
  const original = await session.read("businesses", session.business);
  await page.goto("/app/settings#business-profile");
  const form = page.locator("#business-profile form");
  for (const city of [`Pilot city ${Date.now()}`, original.city || ""]) {
    await form.locator('input[name="city"]').fill(city);
    const saved = page.waitForResponse(response => response.request().method() === "PATCH" && response.url().endsWith(`/api/businesses/${session.business}/`));
    await form.locator('button[type="submit"]').click();
    expect((await saved).ok()).toBeTruthy();
    expect((await session.read("businesses", session.business)).city).toBe(city);
    await page.reload();
    await expect(form.locator('input[name="city"]')).toHaveValue(city);
  }
});

test("timeline search opens the persisted event and navigates to its actual lead", async ({ page }) => {
  const session = await ownerSession(page);
  const client = await session.create("clients", { full_name: `Pilot timeline ${Date.now()}` });
  const lead = await session.create("leads", { client: client.id, source: "manual", message: "Timeline acceptance" });
  await page.goto("/app/timeline");
  const response = page.waitForResponse(item => item.request().method() === "GET" && item.url().includes("/api/activity-events/") && new URL(item.url()).searchParams.get("q") === client.full_name);
  await page.getByRole("searchbox", { name: "Поиск по событиям", exact: true }).fill(client.full_name);
  const found = await response;
  expect(found.ok()).toBeTruthy();
  const payload = await found.json();
  const event = payload.results.find((item: { entity_type: string; entity_id: string }) => item.entity_type.toLowerCase() === "lead" && String(item.entity_id) === String(lead.id));
  expect(event).toBeTruthy();
  await page.locator(`[data-testid="timeline-event-${event.id}"]:visible`).first().click();
  const inspector = page.getByTestId("timeline-details");
  await expect(inspector).toContainText(client.full_name);
  await inspector.locator(`a[href="/app/leads/${lead.id}"]`).click();
  await expect(page).toHaveURL(new RegExp(`/app/leads/${lead.id}$`));
  expect((await session.read("leads", lead.id)).client).toBe(client.id);
});
