import { expect, test, type APIRequestContext, type Page } from "@playwright/test";
import { spawnSync } from "node:child_process";
import path from "node:path";

const password = process.env.E2E_PASSWORD || "ZaniTest123!";
const apiBaseURL = process.env.E2E_API_BASE_URL || "http://127.0.0.1:8000";
const ownerEmail = process.env.E2E_OWNER_EMAIL || "business_owner@example.com";
const operatorEmail =
  process.env.E2E_OPERATOR_EMAIL || "business_operator@example.com";

type TokenPayload = { access: string };
type ListPayload<T> = T[] | { results: T[] };

function unwrapList<T>(payload: ListPayload<T>) {
  return Array.isArray(payload) ? payload : payload.results || [];
}

function authHeaders(tokens: TokenPayload) {
  return { Authorization: `Bearer ${tokens.access}` };
}

async function login(page: Page) {
  await page.context().clearCookies();
  await page.goto("/login");
  await page.locator('form input[type="email"]').first().fill(ownerEmail);
  await page.locator('form input[type="password"]').first().fill(password);
  const tokenResponse = page.waitForResponse(
    (response) =>
      response.request().method() === "POST" &&
      response.url().endsWith("/api/auth/token/"),
  );
  await page.locator('form button[type="submit"]').click();
  const response = await tokenResponse;
  expect(response.ok()).toBeTruthy();
  await expect(page).toHaveURL(/\/app/);
  await expect(page.locator("main").first()).toBeVisible();
  return (await response.json()) as TokenPayload;
}

async function getBusinessId(
  request: APIRequestContext,
  tokens: TokenPayload,
) {
  const response = await request.get(`${apiBaseURL}/api/auth/me/`, {
    headers: authHeaders(tokens),
  });
  expect(response.ok()).toBeTruthy();
  const payload = await response.json();
  const businessId = payload.businesses?.[0]?.id;
  expect(businessId).toBeTruthy();
  return businessId as number;
}

test.describe("FC-006 pilot merchant journeys", () => {
  test("task created in UI delivers one scheduled reminder and opens its saved card", async ({ page }) => {
    test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Requires the isolated quality-gate database and safe provider environment");
    test.setTimeout(90_000);
    expect(process.env.DATABASE_URL).toMatch(/zani-quality-gate-[^/]+\/gate\.sqlite3$/);
    expect(process.env.E2E_PYTHON).toBeTruthy();
    const tokens = await login(page);
    const headers = authHeaders(tokens);
    const membersResponse = await page.request.get(`${apiBaseURL}/api/team/members/`, { headers });
    const members = unwrapList<{ role: string; user: { email: string; full_name: string } }>(await membersResponse.json());
    const owner = members.find(member => member.user.email === ownerEmail)!;
    const title = `Scheduled reminder ${Date.now()}`;
    await page.goto("/app/tasks");
    await page.locator('[data-testid="page-primary-action"]:visible').click();
    const dialog = page.getByRole("dialog");
    await dialog.getByLabel("Название", { exact: true }).fill(title);
    await dialog.getByRole("button", { name: /^Исполнитель / }).click();
    await page.getByRole("option").filter({ hasText: owner.user.full_name || ownerEmail }).click();
    const past = await page.evaluate(() => {
      const date = new Date(Date.now() - 120_000);
      return new Date(date.getTime() - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 16);
    });
    await dialog.getByLabel("Напоминание", { exact: true }).fill(past);
    const saved = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/api/tasks/"));
    await dialog.getByRole("button", { name: "Сохранить", exact: true }).click();
    const response = await saved;
    expect(response.status()).toBe(201);
    const task = await response.json();
    expect(new Date(task.reminder_at).getTime()).toBeLessThan(Date.now());
    await expect(dialog).not.toBeVisible();
    for (let attempt = 0; attempt < 2; attempt += 1) {
      const tick = spawnSync(process.env.E2E_PYTHON!, ["manage.py", "process_due_notifications"], {
        cwd: path.resolve(process.cwd(), ".."), env: process.env, encoding: "utf8", timeout: 30_000,
      });
      expect(tick.status, tick.stderr || String(tick.error || "")).toBe(0);
    }
    const notifications = await page.request.get(`${apiBaseURL}/api/notifications/?category=tasks`, { headers });
    expect(notifications.ok()).toBeTruthy();
    const reminders = unwrapList<{ text: string; action_url: string; status: string }>(await notifications.json())
      .filter(item => item.text === `Напоминание: ${title}`);
    expect(reminders).toHaveLength(1);
    expect(reminders[0].status).toBe("sent");
    await page.reload();
    await page.getByTestId("header-notifications-trigger").click();
    await expect(page.getByText(`Напоминание: ${title}`, { exact: true })).toBeVisible();
    await page.getByText(`Напоминание: ${title}`, { exact: true }).locator("../../..").getByRole("button", { name: "Открыть задачу", exact: true }).click();
    await expect(page).toHaveURL(new RegExp(`/app/tasks\\?task=${task.id}`));
    await expect(page.getByText(title, { exact: true }).first()).toBeVisible();
    const readback = await page.request.get(`${apiBaseURL}/api/tasks/${task.id}/`, { headers });
    expect((await readback.json()).reminder_at).toBe(task.reminder_at);
  });

  test("team access toggle retains specialist and task until manual reassignment", async ({ page, request }) => {
    test.setTimeout(90_000);
    const tokens = await login(page);
    const business = await getBusinessId(page.request, tokens);
    const headers = authHeaders(tokens);
    const membersResponse = await page.request.get(`${apiBaseURL}/api/team/members/?business=${business}`, { headers });
    expect(membersResponse.ok()).toBeTruthy();
    const members = unwrapList<{ id: number; role: string; user: { id: number; email: string } }>(await membersResponse.json());
    const operator = members.find(member => member.user.email === operatorEmail)!;
    const manager = members.find(member => member.role === "manager")!;
    const owner = members.find(member => member.role === "owner")!;
    expect(operator && manager && owner).toBeTruthy();
    const oldSession = await request.post(`${apiBaseURL}/api/auth/token/`, { data: { email: operatorEmail, password } });
    expect(oldSession.ok()).toBeTruthy();
    const oldHeaders = authHeaders(await oldSession.json());
    const taskResponse = await page.request.post(`${apiBaseURL}/api/tasks/`, {
      headers, data: { business, title: `Retained assignment ${Date.now()}`, assignee: operator.user.id },
    });
    expect(taskResponse.ok()).toBeTruthy();
    const task = await taskResponse.json();
    const resourcesResponse = await page.request.get(`${apiBaseURL}/api/resources/?search=${encodeURIComponent(operatorEmail)}`, { headers });
    expect(resourcesResponse.ok()).toBeTruthy();
    let resource = unwrapList<{ id: number; linked_user: number }>(await resourcesResponse.json())
      .find(item => item.linked_user === operator.user.id);
    if (!resource) {
      const resourceResponse = await page.request.post(`${apiBaseURL}/api/resources/`, {
        headers, data: { business, name: `Retained specialist ${Date.now()}`, resource_type: "staff", linked_user: operator.user.id, is_active: true },
      });
      expect(resourceResponse.ok(), await resourceResponse.text()).toBeTruthy();
      resource = await resourceResponse.json();
    }
    expect(resource).toBeTruthy();
    expect((await request.get(`${apiBaseURL}/api/tasks/${task.id}/`, { headers: oldHeaders })).ok()).toBeTruthy();
    await page.goto("/app/settings#team-access");
    await page.getByTestId("team-member-select").selectOption(String(owner.id));
    await expect(page.getByTestId("team-access-toggle")).toHaveCount(0);
    await page.getByTestId("team-member-select").selectOption(String(operator.id));
    async function toggle() {
      await page.getByTestId("team-access-toggle").click();
      const updated = page.waitForResponse(response => response.request().method() === "PATCH" && response.url().endsWith(`/api/team/members/${operator.id}/`));
      await page.getByRole("dialog").getByRole("button").last().click();
      const response = await updated;
      expect(response.ok()).toBeTruthy();
      return response.json();
    }
    try {
      expect((await toggle()).is_active).toBe(false);
      const denied = await request.get(`${apiBaseURL}/api/tasks/${task.id}/`, { headers: oldHeaders });
      expect([401, 403, 404]).toContain(denied.status());
      const retainedTask = await page.request.get(`${apiBaseURL}/api/tasks/${task.id}/`, { headers });
      expect(await retainedTask.json()).toMatchObject({ assignee: operator.user.id, status: "open" });
      const retainedResource = await page.request.get(`${apiBaseURL}/api/resources/${resource!.id}/`, { headers });
      expect(await retainedResource.json()).toMatchObject({ linked_user: operator.user.id, is_active: true });
      await page.goto(`/app/tasks/${task.id}`);
      await page.locator("select").filter({ has: page.locator(`option[value="${manager.user.id}"]`) }).selectOption(String(manager.user.id));
      const assigned = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith(`/api/tasks/${task.id}/assign/`));
      await page.getByRole("button", { name: /Сохранить исполнителя|Save assignee/ }).click();
      expect((await assigned).ok()).toBeTruthy();
      const reassigned = await page.request.get(`${apiBaseURL}/api/tasks/${task.id}/`, { headers });
      expect((await reassigned.json()).assignee).toBe(manager.user.id);
      await page.goto("/app/settings#team-access");
      await page.getByTestId("team-member-select").selectOption(String(operator.id));
      expect((await toggle()).is_active).toBe(true);
    } finally {
      const restore = await page.request.patch(`${apiBaseURL}/api/team/members/${operator.id}/`, { headers, data: { is_active: true } });
      expect(restore.ok()).toBeTruthy();
    }
  });

  test("duplicate client preview and confirmed merge transfer the linked lead", async ({ page, isMobile }) => {
    test.setTimeout(90_000);
    const tokens = await login(page);
    const business = await getBusinessId(page.request, tokens);
    const headers = authHeaders(tokens);
    const unique = Date.now();
    const clients = [];
    for (const name of ["Target", "Duplicate"]) {
      const response = await page.request.post(`${apiBaseURL}/api/clients/`, {
        headers, data: { business, full_name: `${name} ${unique}`, email: `merge-${unique}@example.com`, source: "manual" },
      });
      expect(response.ok()).toBeTruthy();
      clients.push(await response.json());
    }
    const [target, duplicate] = clients;
    const leadResponse = await page.request.post(`${apiBaseURL}/api/leads/`, {
      headers, data: { business, client: duplicate.id, source: "manual", message: "Preserve merge history" },
    });
    expect(leadResponse.ok()).toBeTruthy();
    const lead = await leadResponse.json();
    await page.goto("/app/clients");
    if (isMobile) {
      await page.getByRole("button").filter({ has: page.getByRole("heading", { name: target.full_name, exact: true }) }).click();
    } else {
      await page.locator(`[data-testid="client-row-action-open"][data-client-id="${target.id}"]`).click();
    }
    await page.getByTestId("crm-entity-drawer").getByRole("button", { name: /^(Изменить|Edit|Өзгерту)$/ }).click();
    const previewResponse = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith(`/api/clients/${target.id}/merge-dry-run/`));
    await page.getByTestId("client-action-form").getByRole("button", { name: /Объединить в текущего|Merge into current/ }).click();
    expect((await previewResponse).ok()).toBeTruthy();
    const before = await page.request.get(`${apiBaseURL}/api/leads/${lead.id}/`, { headers });
    expect((await before.json()).client).toBe(duplicate.id);
    const mergedResponse = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith(`/api/clients/${target.id}/merge/`));
    await page.getByRole("button", { name: /^(Объединить клиентов|Merge clients)$/ }).click();
    expect((await mergedResponse).ok()).toBeTruthy();
    const after = await page.request.get(`${apiBaseURL}/api/leads/${lead.id}/`, { headers });
    expect(after.ok()).toBeTruthy();
    expect((await after.json()).client).toBe(target.id);
    await page.reload();
    await expect(isMobile
      ? page.getByRole("heading", { name: duplicate.full_name, exact: true })
      : page.locator(`[data-testid="client-row-action-open"][data-client-id="${duplicate.id}"]`)).toHaveCount(0);
    const preserved = await page.request.get(`${apiBaseURL}/api/clients/${target.id}/`, { headers });
    expect(preserved.ok()).toBeTruthy();
    expect((await preserved.json()).email).toBe(`merge-${unique}@example.com`);
  });

  test("manual receipt and refund persist once through the client journal", async ({ page }) => {
    test.setTimeout(90_000);
    const tokens = await login(page);
    const business = await getBusinessId(page.request, tokens);
    const headers = authHeaders(tokens);
    const created = await page.request.post(`${apiBaseURL}/api/clients/`, {
      headers, data: { business, full_name: `Journal ${Date.now()}`, source: "manual" },
    });
    expect(created.ok()).toBeTruthy();
    const client = await created.json();
    await page.goto(`/app/clients/${client.id}`);
    await page.getByTestId("client-payments-open").click();
    await page.getByTestId("payment-add").click();
    const form = page.getByTestId("payment-form");
    await form.getByLabel(/^(Сумма|Amount|Сома) \(/).fill("1250.50");
    const receiptResponse = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/api/client-payments/"));
    await form.locator('button[type="submit"]').click();
    const receiptResult = await receiptResponse;
    expect(receiptResult.ok()).toBeTruthy();
    const receipt = await receiptResult.json();
    const row = page.getByTestId(`payment-row-${receipt.id}`);
    await expect(row).toContainText("1250.50");
    await row.getByRole("button").click();
    await form.getByLabel(/^(Сумма|Amount|Сома) \(/).fill("250.50");
    await form.locator("textarea").first().fill("Synthetic partial refund");
    const refundResponse = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/api/client-payments/"));
    await form.locator('button[type="submit"]').click();
    const refundResult = await refundResponse;
    expect(refundResult.ok()).toBeTruthy();
    const refund = await refundResult.json();
    expect(refund).toMatchObject({ original: receipt.id, kind: "refund", amount: "250.50" });
    // Replaying the exact submitted command must not add another journal entry.
    const replay = await page.request.post(`${apiBaseURL}/api/client-payments/`, {
      headers, data: refundResult.request().postDataJSON(),
    });
    expect(replay.ok()).toBeTruthy();
    expect((await replay.json()).id).toBe(refund.id);
    await page.reload();
    await page.getByTestId("client-payments-open").click();
    await expect(page.getByTestId(`payment-row-${refund.id}`)).toBeVisible();
    const persisted = await page.request.get(`${apiBaseURL}/api/client-payments/?business=${business}&client=${client.id}`, { headers });
    expect(persisted.ok()).toBeTruthy();
    const journal = await persisted.json();
    expect(journal.count).toBe(2);
    expect(journal.results.find((item: { id: number }) => item.id === receipt.id)).toMatchObject({ refunded_amount: "250.50", remaining_amount: "1000.00" });
  });

  test("client archive and undo restore persist through the workspace", async ({ page }) => {
    const tokens = await login(page);
    const business = await getBusinessId(page.request, tokens);
    const headers = authHeaders(tokens);
    const created = await page.request.post(`${apiBaseURL}/api/clients/`, {
      headers, data: { business, full_name: `Archive ${Date.now()}`, source: "manual" },
    });
    expect(created.ok()).toBeTruthy();
    const client = await created.json();
    await page.goto(`/app/clients/${client.id}`);
    await page.getByRole("button", { name: /^(Архивировать|Archive|Мұрағаттау)$/ }).click();
    const dialog = page.getByRole("dialog");
    await dialog.locator("textarea").fill("Synthetic archive acceptance");
    const archived = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith(`/api/clients/${client.id}/archive/`));
    await dialog.getByRole("button").last().click();
    expect((await archived).ok()).toBeTruthy();
    const restored = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith(`/api/clients/${client.id}/restore/`));
    await page.getByRole("button", { name: /^(Отменить|Undo|Болдырмау)$/ }).click();
    expect((await restored).ok()).toBeTruthy();
    const persisted = await page.request.get(`${apiBaseURL}/api/clients/${client.id}/`, { headers });
    expect(persisted.ok()).toBeTruthy();
    expect((await persisted.json()).is_archived).toBe(false);
    await page.goto(`/app/clients/${client.id}`);
    await expect(page.getByText(client.full_name).first()).toBeVisible();
  });

  test("ZD-015 owner dashboard displays the persisted business-day appointment count", async ({ page }) => {
    const metricsResponse = page.waitForResponse(
      (response) => response.request().method() === "GET"
        && response.url().includes("/api/work-queues/"),
    );
    await login(page);
    const response = await metricsResponse;
    expect(response.ok()).toBeTruthy();
    const metrics = await response.json();
    expect(Number.isInteger(metrics.summary.today_appointments)).toBeTruthy();
    const card = page.getByTestId("dashboard-metric-today_appointments");
    await expect(card.locator(".tabular-nums")).toHaveText(String(metrics.summary.today_appointments));
    await expect(card).toHaveAttribute("href", `/app/calendar?date=${metrics.day}&view=day`);
  });

  test("FC-J06 import validation, duplicates and visible records persist through the Leads UI", async ({
    page,
  }) => {
    test.setTimeout(180_000);
    const tokens = await login(page);
    const businessId = await getBusinessId(page.request, tokens);
    const headers = authHeaders(tokens);
    const unique = Date.now();
    const marker = `FC-J06-${unique}`;
    const phone = `+7706${String(unique).slice(-7)}`;

    const clientResponse = await page.request.post(
      `${apiBaseURL}/api/clients/`,
      {
        headers,
        data: {
          business: businessId,
          full_name: `Certification client ${unique}`,
          phone,
          email: `fc-j06-${unique}@example.com`,
          source: "manual",
        },
      },
    );
    expect(clientResponse.ok()).toBeTruthy();

    await page.goto("/app/leads");
    await expect(page.getByTestId("leads-workspace-ready")).toBeVisible();
    await page.getByTestId("leads-filter-toolbar").getByTestId("row-actions-trigger").click();
    await page.getByRole("menuitem", { name: /Импорт/ }).click();
    await expect(page.getByTestId("leads-import-modal")).toBeVisible();

    const csv = [
      "full_name,phone,email,service_name,source,message,status",
      `Certification client ${unique},${phone},fc-j06-${unique}@example.com,,landing,${marker},new`,
    ].join("\n");
    await page.getByTestId("import-file").setInputFiles({
      name: `fc-j06-${unique}.csv`,
      mimeType: "text/csv",
      buffer: Buffer.from(csv, "utf8"),
    });

    const previewResponse = page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        response.url().endsWith("/api/import-jobs/"),
    );
    await page.getByTestId("import-preview").click();
    const preview = await previewResponse;
    expect(preview.status()).toBe(201);
    const previewPayload = await preview.json();
    expect(previewPayload.status).toBe("previewed");
    expect(previewPayload.errors_json?.rows || []).toEqual([]);
    expect(previewPayload.duplicates_json?.rows?.length).toBeGreaterThan(0);
    await expect(page.getByTestId("import-duplicates")).toBeVisible();

    const confirmResponse = page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        /\/api\/import-jobs\/\d+\/confirm\/$/.test(response.url()),
    );
    await page.getByTestId("import-confirm").click();
    const confirmed = await confirmResponse;
    expect(confirmed.ok()).toBeTruthy();
    const confirmedPayload = await confirmed.json();
    expect(confirmedPayload.status).toBe("imported");
    expect(confirmedPayload.imported_count).toBe(1);

    await page.keyboard.press("Escape");
    await expect(page.getByTestId("leads-import-modal")).toHaveCount(0);
    await page.getByTestId("leads-search-input").fill(marker);
    await expect(
      page
        .locator(
          '[data-testid="lead-row-keyboard-open"]:visible, [data-testid="lead-mobile-row-open"]:visible',
        )
        .filter({ hasText: `Certification client ${unique}` }),
    ).toBeVisible();

    const leadsResponse = await page.request.get(
      `${apiBaseURL}/api/leads/?search=${encodeURIComponent(marker)}`,
      { headers },
    );
    expect(leadsResponse.ok()).toBeTruthy();
    const leads = unwrapList(await leadsResponse.json());
    expect(leads).toHaveLength(1);
    expect(leads[0]).toMatchObject({
      business: businessId,
      message: marker,
      source: "landing",
    });
  });

  test("FC-J07 owner role change is applied by the Team UI and restored", async ({
    page,
  }) => {
    test.setTimeout(180_000);
    const tokens = await login(page);
    const businessId = await getBusinessId(page.request, tokens);
    const headers = authHeaders(tokens);
    const membersResponse = await page.request.get(
      `${apiBaseURL}/api/team/members/?business=${businessId}`,
      { headers },
    );
    expect(membersResponse.ok()).toBeTruthy();
    const members = unwrapList<{
      id: number;
      role: string;
      business_role: number | null;
      user: { email: string };
    }>(await membersResponse.json());
    const operator = members.find(
      (member) => member.user.email === operatorEmail,
    );
    expect(operator).toBeTruthy();
    if (!operator) return;

    const originalRole = operator.role;
    const originalBusinessRole = operator.business_role;
    let needsRestore = false;
    try {
      await page.goto("/app/settings#team-access");
      await expect(page.getByTestId("team-member-select")).toBeAttached();
      await page.getByTestId("team-member-select").selectOption(String(operator.id));
      await expect(page.getByTestId("team-role-select")).toHaveValue(originalRole);

      const updateResponse = page.waitForResponse(
        (response) =>
          response.request().method() === "PATCH" &&
          response.url().endsWith(`/api/team/members/${operator.id}/`),
      );
      await page.getByTestId("team-role-select").selectOption("manager");
      const updated = await updateResponse;
      expect(updated.ok()).toBeTruthy();
      expect((await updated.json()).role).toBe("manager");
      needsRestore = true;

      const persistedResponse = await page.request.get(
        `${apiBaseURL}/api/team/members/?business=${businessId}`,
        { headers },
      );
      const persistedMembers = unwrapList<{ id: number; role: string }>(
        await persistedResponse.json(),
      );
      expect(
        persistedMembers.find((member) => member.id === operator.id)?.role,
      ).toBe("manager");

      const restoreResponse = page.waitForResponse(
        (response) =>
          response.request().method() === "PATCH" &&
          response.url().endsWith(`/api/team/members/${operator.id}/`),
      );
      await page.getByTestId("team-role-select").selectOption(originalRole);
      expect((await restoreResponse).ok()).toBeTruthy();
      needsRestore = false;
    } finally {
      if (needsRestore) {
        const restore = await page.request.patch(
          `${apiBaseURL}/api/team/members/${operator.id}/`,
          {
            headers,
            data: {
              role: originalRole,
              business_role: originalBusinessRole,
            },
          },
        );
        expect(restore.ok()).toBeTruthy();
      }
    }
  });

  test("FC-J10 grounded AI suggestion requires approval and persists task plus audit", async ({
    page,
  }) => {
    test.setTimeout(180_000);
    const tokens = await login(page);
    const businessId = await getBusinessId(page.request, tokens);
    const headers = authHeaders(tokens);

    await page.goto("/app/ai-assistant");
    await expect(page.getByTestId("ai-action-workflow")).toBeVisible();
    const sourceSelect = page.getByTestId("ai-action-source");
    const conversationId = await sourceSelect
      .locator("option")
      .nth(1)
      .getAttribute("value");
    expect(conversationId).toBeTruthy();
    if (!conversationId) return;
    await sourceSelect.selectOption(conversationId);
    await page
      .getByTestId("ai-action-prompt")
      .fill("Create a grounded follow-up task for this conversation");

    const suggestResponse = page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        response.url().endsWith("/api/ai/tools/suggest/"),
    );
    await page.getByTestId("ai-action-suggest").click();
    const suggested = await suggestResponse;
    expect(suggested.status()).toBe(201);
    const suggestedPayload = await suggested.json();
    const taskAction = suggestedPayload.suggested_actions.find(
      (action: { tool_name: string }) => action.tool_name === "create_task",
    );
    expect(taskAction).toBeTruthy();
    expect(String(taskAction.conversation)).toBe(conversationId);
    await expect(page.getByTestId("ai-action-source-chip").first()).toHaveText(
      `CONVERSATION-${conversationId}`,
    );

    await page.getByTestId(`ai-action-run-${taskAction.id}`).click();
    const approvalDialog = page.getByRole("dialog");
    await expect(approvalDialog).toBeVisible();
    const tasksBeforeCancel = await page.request.get(`${apiBaseURL}/api/tasks/`, { headers });
    expect(tasksBeforeCancel.ok()).toBeTruthy();
    const beforeCancelCount = (await tasksBeforeCancel.json()).count;
    const approvalWrites: string[] = [];
    const captureApprovalWrite = (request: import("@playwright/test").Request) => {
      if (request.method() === "POST" && /\/api\/ai\/(approval-requests|tools\/\d+\/execute)/.test(request.url())) approvalWrites.push(request.url());
    };
    page.on("request", captureApprovalWrite);
    await approvalDialog.getByRole("button", { name: "Отмена", exact: true }).click();
    await expect(approvalDialog).not.toBeVisible();
    const tasksAfterCancel = await page.request.get(`${apiBaseURL}/api/tasks/`, { headers });
    expect((await tasksAfterCancel.json()).count).toBe(beforeCancelCount);
    expect(approvalWrites).toHaveLength(0);
    page.off("request", captureApprovalWrite);
    await page.getByTestId(`ai-action-run-${taskAction.id}`).click();
    await expect(approvalDialog).toBeVisible();
    await approvalDialog.locator("textarea").fill("Owner confirmed this action");
    const executeResponse = page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        response.url().endsWith(`/api/ai/tools/${taskAction.id}/execute/`),
    );
    await approvalDialog.getByRole("button").last().click();
    const executed = await executeResponse;
    expect(executed.ok()).toBeTruthy();
    const executedPayload = await executed.json();
    expect(executedPayload.status).toBe("executed");
    const taskId = executedPayload.output_json?.task_id;
    expect(taskId).toBeTruthy();
    await expect(page.getByText(new RegExp(`ID: ${taskId}`))).toBeVisible();

    const taskResponse = await page.request.get(
      `${apiBaseURL}/api/tasks/${taskId}/`,
      { headers },
    );
    expect(taskResponse.ok()).toBeTruthy();
    expect(await taskResponse.json()).toMatchObject({
      business: businessId,
      conversation: Number(conversationId),
    });

    const auditResponse = await page.request.get(
      `${apiBaseURL}/api/security/audit/?business=${businessId}&entity_type=AIToolCallLog`,
      { headers },
    );
    expect(auditResponse.ok()).toBeTruthy();
    const auditLogs = unwrapList<{
      entity_id: string;
      metadata: Record<string, unknown>;
    }>(await auditResponse.json());
    expect(
      auditLogs.some(
        (entry) =>
          entry.entity_id === String(taskAction.id) &&
          entry.metadata?.status === "executed" &&
          entry.metadata?.approval_id,
      ),
    ).toBeTruthy();
  });
});
