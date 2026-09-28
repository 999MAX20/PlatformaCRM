import { expect, test, type Page } from "@playwright/test";

const api = process.env.E2E_API_BASE_URL || "http://127.0.0.1:8000";

async function leadFixture(page: Page, namePrefix = "") {
  await page.goto("/login");
  await page.locator('form input[type="email"]').fill(process.env.E2E_OWNER_EMAIL || "business_owner@example.com");
  await page.locator('form input[type="password"]').fill(process.env.E2E_PASSWORD || "ZaniTest123!");
  const loggedIn = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/api/auth/token/"));
  await page.locator('form button[type="submit"]').click();
  const response = await loggedIn;
  expect(response.ok()).toBeTruthy();
  const headers = { Authorization: `Bearer ${(await response.json()).access}` };
  await expect(page).toHaveURL(/\/app/);
  const me = await page.request.get(`${api}/api/auth/me/`, { headers });
  const business = (await me.json()).businesses[0].id;
  const marker = `${namePrefix}Pilot content ${Date.now()}`;
  const client = await page.request.post(`${api}/api/clients/`, { headers, data: { business, full_name: marker, phone: "+77770001133" } });
  expect(client.status()).toBe(201);
  const lead = await page.request.post(`${api}/api/leads/`, { headers, data: { business, client: (await client.json()).id, message: marker, source: "manual" } });
  expect(lead.status()).toBe(201);
  const record = await lead.json();
  async function openDrawer() {
    await page.goto("/app/leads");
    await page.getByTestId("leads-search-input").fill(marker);
    const row = page.locator('[data-testid="lead-row-keyboard-open"]:visible, [data-testid="lead-mobile-row-open"]:visible').filter({ hasText: marker });
    await expect(row).toHaveCount(1);
    await row.click();
    await expect(page.getByTestId("crm-entity-drawer")).toBeVisible();
  }
  return { headers, marker, record, openDrawer };
}

test("lead notes and private attachment upload rename and download survive reopening", async ({ page, playwright }) => {
  test.setTimeout(120_000);
  const fixture = await leadFixture(page);
  await fixture.openDrawer();
  const drawer = page.getByTestId("crm-entity-drawer");
  await drawer.getByTestId("crm-entity-tab-notes").click();
  const note = `${fixture.marker} preserved note`;
  await drawer.locator("textarea").fill(note);
  const savedNote = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith(`/api/leads/${fixture.record.id}/add-note/`));
  await drawer.getByRole("button", { name: "Добавить комментарий", exact: true }).click();
  expect((await savedNote).ok()).toBeTruthy();
  await expect(drawer.getByText(note, { exact: true })).toBeVisible();
  await drawer.getByTestId("crm-entity-tab-files").click();
  const contents = `Private synthetic attachment for ${fixture.marker}`;
  await drawer.getByTestId("crm-attachment-input").setInputFiles({ name: "pilot-content.txt", mimeType: "text/plain", buffer: Buffer.from(contents) });
  const uploaded = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/api/file-attachments/"));
  await drawer.getByRole("button", { name: "Загрузить 1", exact: true }).click();
  const uploadedResponse = await uploaded;
  expect(uploadedResponse.status()).toBe(201);
  const attachment = await uploadedResponse.json();
  expect(attachment.scan_status).toBe("pending");
  expect(attachment.download_url).toBe("");
  await expect(drawer.locator('[data-testid="attachment-scan-status"][data-scan-status="clean"]')).toBeVisible({ timeout: 20000 });
  await expect(drawer.getByText("pilot-content.txt", { exact: true })).toBeVisible();
  await drawer.getByRole("button", { name: "Действия с файлом", exact: true }).click();
  await drawer.getByRole("button", { name: "Переименовать", exact: true }).click();
  const rename = page.getByRole("dialog", { name: "Переименовать", exact: true });
  await rename.getByLabel("Название файла", { exact: true }).fill("pilot-renamed.txt");
  const renamed = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith(`/api/file-attachments/${attachment.id}/rename/`));
  await rename.getByRole("button", { name: "Сохранить", exact: true }).click();
  expect((await renamed).ok()).toBeTruthy();
  await expect(rename).not.toBeVisible();
  await fixture.openDrawer();
  await drawer.getByTestId("crm-entity-tab-notes").click();
  await expect(drawer.getByText(note, { exact: true })).toBeVisible();
  await drawer.getByTestId("crm-entity-tab-files").click();
  await expect(drawer.getByText("pilot-renamed.txt", { exact: true })).toBeVisible();
  await drawer.getByRole("button", { name: "Действия с файлом", exact: true }).click();
  const downloaded = page.waitForEvent("download");
  await drawer.getByRole("button", { name: "Скачать", exact: true }).click();
  const download = await downloaded;
  expect(download.suggestedFilename()).toBe("pilot-renamed.txt");
  const stream = await download.createReadStream();
  const chunks: Buffer[] = [];
  for await (const chunk of stream!) chunks.push(Buffer.from(chunk));
  expect(Buffer.concat(chunks).toString("utf8")).toBe(contents);
  const unauthenticated = await playwright.request.newContext();
  try {
    const denied = await unauthenticated.get(`${api}/api/file-attachments/${attachment.id}/download/`);
    expect([401, 403]).toContain(denied.status());
  } finally {
    await unauthenticated.dispose();
  }
  const card = await page.request.get(`${api}/api/leads/${fixture.record.id}/crm-card/`, { headers: fixture.headers });
  expect(card.ok()).toBeTruthy();
  const persisted = await card.json();
  expect(persisted.notes.filter((item: { text: string }) => item.text === note)).toHaveLength(1);
  expect(persisted.attachments.filter((item: { id: number; original_name: string }) => item.id === attachment.id && item.original_name === "pilot-renamed.txt")).toHaveLength(1);
});

test("quarantined files expose status but cannot be previewed or downloaded", async ({ page }) => {
  test.setTimeout(90000);
  const fixture = await leadFixture(page);
  for (const [marker, state] of [["E2E_SCAN_BLOCK", "infected"], ["E2E_SCAN_ERROR", "error"]]) {
    const uploaded = await page.request.post(`${api}/api/file-attachments/`, {
      headers: fixture.headers,
      multipart: {
        business: String(fixture.record.business), entity_type: "lead", entity_id: String(fixture.record.id),
        file: { name: `${marker}.txt`, mimeType: "text/plain", buffer: Buffer.from(marker) },
      },
    });
    expect(uploaded.status()).toBe(201);
    const attachment = await uploaded.json();
    expect(attachment.scan_status).toBe("pending");
    expect(attachment.download_url).toBe("");
    await expect.poll(async () => {
      const result = await page.request.get(`${api}/api/file-attachments/${attachment.id}/`, { headers: fixture.headers });
      return (await result.json()).scan_status;
    }, { timeout: 15000 }).toBe(state);
    const blocked = await page.request.get(`${api}/api/file-attachments/${attachment.id}/download/`, { headers: fixture.headers });
    expect(blocked.status()).toBe(423);
  }
  await fixture.openDrawer();
  const drawer = page.getByTestId("crm-entity-drawer");
  await drawer.getByTestId("crm-entity-tab-files").click();
  await expect(drawer.locator('[data-scan-status="infected"]')).toBeVisible();
  await expect(drawer.locator('[data-scan-status="error"]')).toBeVisible();
  await drawer.getByRole("button", { name: "Действия с файлом", exact: true }).first().click();
  await expect(drawer.getByRole("button", { name: "Скачать", exact: true })).toBeDisabled();
  await expect(drawer.getByRole("button", { name: "Открыть", exact: true })).toBeDisabled();
});

test("lead CSV export contains only the filtered saved record", async ({ page }) => {
  const fixture = await leadFixture(page, "=");
  await page.goto("/app/leads");
  const filtered = page.waitForResponse(response => {
    const url = new URL(response.url());
    return url.pathname === "/api/leads/" && url.searchParams.get("search") === fixture.marker;
  });
  await page.getByTestId("leads-search-input").fill(fixture.marker);
  expect((await filtered).ok()).toBeTruthy();
  await expect(page.locator('[data-testid="lead-row-keyboard-open"]:visible, [data-testid="lead-mobile-row-open"]:visible')).toHaveCount(1);
  const pending = page.waitForEvent("download");
  await page.getByRole("button", { name: "Экспорт CSV", exact: true }).click();
  const download = await pending;
  expect(download.suggestedFilename()).toBe("PlatformaCRM-leads.csv");
  const stream = await download.createReadStream();
  const chunks: Buffer[] = [];
  for await (const chunk of stream!) chunks.push(Buffer.from(chunk));
  const rows = Buffer.concat(chunks).toString("utf8").trim().split(/\r?\n/);
  expect(rows).toHaveLength(2);
  expect(rows[1]).toContain(`"'${fixture.marker}"`);
  expect(rows[1]).toContain("\"'+77770001133\"");
});

test("client edit tag and linked task retain the original client identity", async ({ page }) => {
  test.setTimeout(90_000);
  const fixture = await leadFixture(page);
  const clientId = fixture.record.client;
  await page.goto(`/app/clients/${clientId}`);
  await page.getByTestId("client-edit-action").click();
  const edit = page.getByRole("dialog", { name: "Редактировать клиента", exact: true });
  const name = `${fixture.marker} updated`;
  await edit.locator('input[name="full_name"]').fill(name);
  const edited = page.waitForResponse(response => response.request().method() === "PATCH" && response.url().endsWith(`/api/clients/${clientId}/`));
  await edit.getByTestId("client-action-submit").click();
  expect((await edited).ok()).toBeTruthy();
  await expect(edit).not.toBeVisible();
  await page.getByRole("button", { name: "Добавить тег", exact: true }).click();
  const tagDialog = page.getByRole("dialog", { name: "Добавить тег", exact: true });
  const tag = `Pilot-tag-${Date.now()}`;
  await tagDialog.getByLabel("Название тега", { exact: true }).fill(tag);
  const tagged = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/api/tagged-objects/"));
  await tagDialog.getByRole("button", { name: "Добавить тег", exact: true }).click();
  expect((await tagged).status()).toBe(201);
  await expect(tagDialog).not.toBeVisible();
  await page.reload();
  await expect(page.getByText(tag, { exact: true })).toBeVisible();
  const readback = await page.request.get(`${api}/api/clients/${clientId}/`, { headers: fixture.headers });
  expect((await readback.json()).full_name).toBe(name);
  await page.locator('[data-crm-action-id="create_task"]').click();
  await expect(page).toHaveURL(/\/app\/tasks(?:\?|$)/);
  const taskDialog = page.getByRole("dialog");
  await taskDialog.getByLabel("Название", { exact: true }).fill(`${fixture.marker} linked task`);
  const created = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/api/tasks/"));
  await taskDialog.getByRole("button", { name: "Сохранить", exact: true }).click();
  const response = await created;
  expect(response.status()).toBe(201);
  expect((await response.json()).client).toBe(clientId);
  await page.goto(`/app/clients/${clientId}`);
  const card = await page.request.get(`${api}/api/clients/${clientId}/crm-card/`, { headers: fixture.headers });
  const persisted = await card.json();
  expect(persisted.tags.filter((item: { tag_name: string }) => item.tag_name === tag)).toHaveLength(1);
  expect(persisted.tasks.some((item: { title: string }) => item.title === `${fixture.marker} linked task`)).toBe(true);
});

test("deal board drag persists the intended nonterminal stage", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "desktop-chromium", "Native mouse drag; narrow-board layout has separate responsive coverage");
  const fixture = await leadFixture(page);
  const pipelinesResponse = await page.request.get(`${api}/api/pipelines/`, { headers: fixture.headers });
  const pipelineBody = await pipelinesResponse.json();
  const pipelines = pipelineBody.results || pipelineBody;
  const pipeline = pipelines.find((item: { is_default: boolean }) => item.is_default) || pipelines[0];
  const stagesResponse = await page.request.get(`${api}/api/pipeline-stages/?pipeline=${pipeline.id}`, { headers: fixture.headers });
  const stageBody = await stagesResponse.json();
  const stages = (stageBody.results || stageBody).filter((item: { pipeline: number; is_won: boolean; is_lost: boolean }) => item.pipeline === pipeline.id && !item.is_won && !item.is_lost)
    .sort((left: { order: number }, right: { order: number }) => left.order - right.order);
  expect(stages.length).toBeGreaterThanOrEqual(2);
  const created = await page.request.post(`${api}/api/deals/`, {
    headers: fixture.headers,
    data: { business: fixture.record.business, client: fixture.record.client, title: fixture.marker, pipeline: pipeline.id, stage: stages[0].id, next_action_at: new Date(Date.now() + 86400000).toISOString() },
  });
  expect(created.status()).toBe(201);
  const deal = await created.json();
  await page.goto("/app/deals");
  await page.getByTestId("deals-search-input").fill(fixture.marker);
  const source = page.getByTestId(`deals-kanban-stage-${stages[0].id}`).locator("article").filter({ hasText: fixture.marker });
  const target = page.getByTestId(`deals-kanban-stage-${stages[1].id}`);
  await expect(source).toBeVisible();
  const moved = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith(`/api/deals/${deal.id}/move-stage/`));
  await source.dragTo(target.locator("header"));
  expect((await moved).ok()).toBeTruthy();
  await expect(target.locator("article").filter({ hasText: fixture.marker })).toBeVisible();
  await page.reload();
  const readback = await page.request.get(`${api}/api/deals/${deal.id}/`, { headers: fixture.headers });
  expect((await readback.json()).stage).toBe(stages[1].id);
  await expect(target.locator("article").filter({ hasText: fixture.marker })).toBeVisible();
});

test("analytics team CSV downloads actual report columns and authorized rows", async ({ page }) => {
  await leadFixture(page);
  await page.goto("/app/analytics");
  const pending = page.waitForEvent("download");
  const exported = page.waitForResponse(response => response.url().includes("/api/analytics/reports/export/") && response.request().method() === "GET");
  await page.getByRole("button", { name: "CSV команды", exact: true }).first().click();
  const response = await exported;
  expect(response.status()).toBe(200);
  expect(response.headers()["content-type"]).toContain("text/csv");
  const download = await pending;
  expect(download.suggestedFilename()).toBe("manager_performance.csv");
  const stream = await download.createReadStream();
  const chunks: Buffer[] = [];
  for await (const chunk of stream!) chunks.push(Buffer.from(chunk));
  const csv = Buffer.concat(chunks).toString("utf8");
  expect(csv).toBe(await response.text());
  expect(csv.split(/\r?\n/)[0]).toContain("assigned_leads");
  expect(csv.split(/\r?\n/)[0]).toContain("open_tasks");
  expect(csv.trim().split(/\r?\n/).length).toBeGreaterThan(1);
});

for (const action of ["create_lead", "create_deal", "create_appointment", "create_task"]) {
  test(`client ${action} opens its linked creation form`, async ({ page }) => {
    const fixture = await leadFixture(page);
    await page.goto(`/app/clients/${fixture.record.client}`);
    await page.locator(`[data-crm-action-id="${action}"]`).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    // Query propagation alone is not sufficient; the actual form must open.
    if (action === "create_task") {
      await expect(dialog.getByRole("button").filter({ hasText: fixture.marker })).toBeVisible();
    } else if (action === "create_deal") {
      await expect(dialog.locator("select").first()).toHaveValue(String(fixture.record.client));
    } else {
      await expect(dialog.locator('select[name="client"]')).toHaveValue(String(fixture.record.client));
    }
    await expect.poll(() => new URL(page.url()).searchParams.has("create")).toBe(false);
    await dialog.getByRole("button", { name: "Закрыть", exact: true }).click();
    await expect(dialog).not.toBeVisible();
    await page.reload();
    await expect(page.locator("main")).toBeVisible();
    await expect(dialog).not.toBeVisible();
  });
}

test("client creation intent rejects foreign clients in all four workspaces", async ({ page, request }) => {
  const fixture = await leadFixture(page);
  // A second account must not replace the browser's refresh cookie.
  const foreignLogin = await request.post(`${api}/api/auth/token/`, { data: {
    email: process.env.E2E_FOREIGN_OWNER_EMAIL || "foreign_owner@example.com",
    password: process.env.E2E_PASSWORD || "ZaniTest123!",
  } });
  expect(foreignLogin.ok()).toBeTruthy();
  const headers = { Authorization: `Bearer ${(await foreignLogin.json()).access}` };
  const me = await (await request.get(`${api}/api/auth/me/`, { headers })).json();
  const foreign = await request.post(`${api}/api/clients/`, { headers, data: {
    business: me.businesses[0].id, full_name: `${fixture.marker} foreign`,
  } });
  expect(foreign.status()).toBe(201);
  const client = await foreign.json();
  for (const path of ["leads", "deals", "calendar", "tasks"]) {
    const rejected = page.waitForResponse(response => response.request().method() === "GET" && response.url().endsWith(`/api/clients/${client.id}/`));
    await page.goto(`/app/${path}?create=1&client=${client.id}`);
    expect([403, 404]).toContain((await rejected).status());
    await expect(page.getByRole("dialog")).not.toBeVisible();
    await expect(page.locator("main")).not.toContainText(client.full_name);
  }
});

test("specialist cannot open client-linked lead creation", async ({ page }) => {
  await page.goto("/login");
  await page.locator('form input[type="email"]').fill(process.env.E2E_SPECIALIST_EMAIL || "business_specialist@example.com");
  await page.locator('form input[type="password"]').fill(process.env.E2E_PASSWORD || "ZaniTest123!");
  const loggedIn = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/api/auth/token/"));
  await page.locator('form button[type="submit"]').click();
  const tokens = await (await loggedIn).json();
  await expect(page).toHaveURL(/\/app/);
  const headers = { Authorization: `Bearer ${tokens.access}` };
  const me = await (await page.request.get(`${api}/api/auth/me/`, { headers })).json();
  const denied = await page.request.post(`${api}/api/leads/`, { headers, data: { business: me.businesses[0].id, client: 1, source: "manual" } });
  expect(denied.status()).toBe(403);
  await page.goto("/app/leads?create=1&client=1");
  await expect(page.locator("main")).toBeVisible();
  await expect(page.getByRole("dialog")).not.toBeVisible();
});

test("linked lead deal and appointment save the selected client without reselection", async ({ page }) => {
  test.setTimeout(90_000);
  const fixture = await leadFixture(page);
  const client = fixture.record.client;
  const business = fixture.record.business;
  for (const path of ["leads", "deals"]) {
    await page.goto(`/app/${path}?create=1&client=${client}&keep=pilot`);
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await expect.poll(() => new URL(page.url()).searchParams.get("keep")).toBe("pilot");
    if (path === "deals") await dialog.locator('input').first().fill(`${fixture.marker} linked deal`);
    else await dialog.locator("textarea").fill(`${fixture.marker} linked lead`);
    const saved = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith(`/api/${path}/`));
    await dialog.getByTestId(path === "leads" ? "lead-action-submit" : "deal-action-submit").click();
    const response = await saved;
    expect(response.status(), await response.text()).toBe(201);
    const record = await response.json();
    expect(record.client).toBe(client);
    const persisted = await page.request.get(`${api}/api/${path}/${record.id}/`, { headers: fixture.headers });
    expect((await persisted.json()).client).toBe(client);
  }
  const service = await page.request.post(`${api}/api/services/`, { headers: fixture.headers, data: {
    business, name: `${fixture.marker} service`, duration_minutes: 30, price_from: "1000.00",
  } });
  expect(service.status()).toBe(201);
  const resource = await page.request.post(`${api}/api/resources/`, { headers: fixture.headers, data: {
    business, name: `${fixture.marker} specialist`, resource_type: "staff", is_active: true,
  } });
  expect(resource.status()).toBe(201);
  const specialist = await resource.json();
  const preset = await page.request.post(`${api}/api/working-hours/apply-preset/`, { headers: fixture.headers,
    data: { business, resource: specialist.id, preset: "daily_9_20" } });
  expect(preset.ok()).toBeTruthy();
  await page.goto(`/app/calendar?create=1&client=${client}`);
  const dialog = page.getByRole("dialog");
  await expect(dialog.locator('select[name="client"]')).toHaveValue(String(client));
  await dialog.locator('select[name="service"]').locator("..").getByRole("combobox").click();
  await page.getByRole("option", { name: new RegExp(`${fixture.marker} service`) }).click();
  await dialog.locator('select[name="resource"]').locator("..").getByRole("combobox").click();
  await page.getByRole("option", { name: specialist.name, exact: true }).click();
  const tomorrow = new Date(Date.now() + 86_400_000).toISOString().slice(0, 10);
  await dialog.locator('input[name="date"]').fill(tomorrow);
  await expect.poll(() => dialog.locator('select[name="slot"] option').count()).toBeGreaterThan(1);
  await dialog.locator('select[name="slot"]').locator("..").getByRole("combobox").click();
  await page.getByRole("option").nth(1).click();
  const saved = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/api/appointments/"));
  await dialog.getByTestId("appointment-submit").click();
  const response = await saved;
  expect(response.status(), await response.text()).toBe(201);
  const record = await response.json();
  expect(record.client).toBe(client);
  expect(record.resource).toBe(specialist.id);
  const persisted = await page.request.get(`${api}/api/appointments/${record.id}/`, { headers: fixture.headers });
  expect((await persisted.json()).client).toBe(client);
  await page.goto(`/app/calendar/${record.id}`);
  await page.locator('[data-appointment-action-id="cancelled"]').click();
  const cancellation = page.getByRole("dialog");
  await expect(cancellation.getByRole("button").last()).toBeDisabled();
  await cancellation.locator("textarea").fill("Client requested cancellation");
  const cancelled = page.waitForResponse(item => item.request().method() === "POST" && item.url().endsWith(`/api/appointments/${record.id}/cancel/`));
  await cancellation.getByRole("button").last().click();
  expect((await cancelled).ok()).toBeTruthy();
  expect((await (await page.request.get(`${api}/api/appointments/${record.id}/`, { headers: fixture.headers })).json()).status).toBe("cancelled");
  // The cancelled slot is available again, while its history remains.
  const replacement = await page.request.post(`${api}/api/appointments/`, { headers: fixture.headers, data: {
    business, client, resource: specialist.id, service: record.service,
    start_at: record.start_at, end_at: record.end_at, source: "manual",
  } });
  expect(replacement.status(), await replacement.text()).toBe(201);
  const replacementId = (await replacement.json()).id;
  await page.goto(`/app/calendar/${replacementId}`);
  const confirmed = page.waitForResponse(item => item.request().method() === "POST" && item.url().endsWith(`/api/appointments/${replacementId}/confirm/`));
  await page.locator('[data-appointment-action-id="confirmed"]').click();
  expect((await confirmed).ok()).toBeTruthy();
  await page.locator('[data-appointment-action-id="no_show"]').click();
  const missed = page.getByRole("dialog");
  await expect(missed.getByRole("button").last()).toBeDisabled();
  await missed.locator("textarea").fill("Client did not attend");
  const noShow = page.waitForResponse(item => item.request().method() === "POST" && item.url().endsWith(`/api/appointments/${replacementId}/no-show/`));
  await missed.getByRole("button").last().click();
  expect((await noShow).ok()).toBeTruthy();
  await page.reload();
  expect((await (await page.request.get(`${api}/api/appointments/${replacementId}/`, { headers: fixture.headers })).json()).status).toBe("no_show");
});
