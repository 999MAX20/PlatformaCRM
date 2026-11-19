import { readFileSync } from "node:fs";
import { expect, test, type Page } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";
import { ru } from "../src/lib/i18n/ru";

test.beforeEach(() => test.skip(process.env.ZANI_QUALITY_GATE !== "1" || !process.env.MANAGEMENT_FIXTURE, "Requires isolated Management data"));
async function choose(page: Page, label: string, value: string) {
  await page.getByRole("combobox", { name: new RegExp(`^${label}`) }).click();
  await page.getByRole("option", { name: value, exact: true }).click();
}

test("Management configuration governs manual booking, transfer and AI confirmation", async ({ page }, info) => {
  const f = JSON.parse(readFileSync(process.env.MANAGEMENT_FIXTURE!, "utf8")).desktop;
  const session = await crmSession(page, f.email);
  const client = await session.create<{ id: number }>("clients", { full_name: "Booking Client" });
  const staff = await session.create<{ id: number }>("management/staff", { name: "Booking Specialist", locations: [{ branch: f.branch, service_ids: [] }] });
  const service = await session.create<{ id: number }>("management/services", { name: "Booking Service", duration_minutes: 45, price_from: "12345.67", locations: [{ branch: f.branch, specialist_ids: [staff.id], room_ids: [] }] });
  const room = await session.create<{ id: number }>("management/rooms", { name: "Booking Room", branch: f.branch, service_ids: [service.id], inherit_schedule: true });
  for (const resource of [null, staff.id]) await session.action(`branches/${f.branch}/schedule`, { resource, date: "2030-01-07", intervals: [{ start: "09:00", end: "18:00" }] });
  await page.goto(`/app/calendar?date=2030-01-07&branch=${f.branch}`);
  await page.getByRole("button", { name: ru["calendar.newBooking"], exact: true }).first().click();
  const form = page.getByTestId("appointment-form");
  await form.getByRole("button", { name: /^Клиент / }).click();
  await page.getByPlaceholder(ru["common.search"], { exact: true }).fill("Booking Client");
  await page.getByRole("option", { name: "Booking Client", exact: true }).click();
  await form.getByRole("combobox", { name: /^Услуга / }).click();
  await page.getByRole("option", { name: /^Booking Service · 45 / }).click();
  await choose(page, ru["appointment.resource"], "Booking Specialist");
  await choose(page, ru["appointment.slot"], "09:00");
  await form.getByTestId("appointment-submit").click();
  await expect(form).not.toBeVisible();
  let visits = await session.list<any>("appointments");
  const visit = visits.find(row => row.service === service.id)!;
  expect(visit).toMatchObject({ booked_duration_minutes: 45, booked_price: "12345.67", resource: staff.id });
  expect(JSON.stringify(visit.reserved_resources)).toContain("Booking Room");
  await page.goto(`/app/calendar/${visit.id}`);
  await page.locator('[data-appointment-action-id="reschedule"]').click();
  await choose(page, ru["appointment.time"], "10:00 - 10:45");
  await page.getByTestId("appointment-reschedule-submit").click();
  await expect(page.getByTestId("appointment-reschedule-form")).not.toBeVisible();
  expect((await session.read(`appointments/${visit.id}`)).start_at).not.toBe(visit.start_at);
  await expect(page.getByText(/Booking Service.*10:00.*Booking Specialist/)).toBeVisible();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: info.outputPath("manual-transfer.png") });

  const bot = await session.create<{ id: number }>("bots", { name: "Booking Verification", scenario: "crm", status: "draft" });
  const profile = (await session.list<{ id: number; bot: number }>("ai/agent-profiles")).find(row => row.bot === bot.id)!;
  const configured = await page.request.patch(`${process.env.E2E_API_BASE_URL}/api/ai/agent-profiles/${profile.id}/`, {
    headers: session.headers, data: { allowed_tools_json: { tools: ["crm_read", "crm_create", "crm_transition"] } },
  });
  expect(configured.status(), await configured.text()).toBe(200);
  await session.action(`bots/${bot.id}/activate`);
  await page.goto(`/app/ai-agents/${bot.id}/profile`);
  const editor = page.getByTestId("ai-agent-editor");
  await editor.getByRole("button", { name: "Работа с CRM", exact: true }).click();
  await editor.locator("summary").filter({ hasText: "Действия с CRM" }).click();
  for (const [tool_name, args] of [
    ["crm_create", { entity: "appointments", values: { client: client.id, service: service.id, resource: staff.id, branch: f.branch, start_at: "2030-01-07T12:00:00+06:00" } }],
    ["crm_transition", { entity: "appointments", entity_id: visit.id, action: "reschedule", values: { start_at: "2030-01-07T14:00:00+06:00" } }],
  ] as const) {
    const proposal = await session.action("ai/tools/suggest", { business: session.business, agent: bot.id, tool_name, arguments: args });
    await page.route("**/api/ai/crm/plan/", route => route.fulfill({ json: { question: "", suggested_actions: proposal.suggested_actions } }), { times: 1 });
    await editor.getByRole("textbox", { name: "Что нужно сделать?", exact: true }).fill(tool_name);
    await editor.getByRole("button", { name: "Подготовить действие", exact: true }).click();
    await editor.getByRole("region", { name: "Проверка действия", exact: true }).getByRole("button", { name: "Подтвердить", exact: true }).click();
    const executed = page.waitForResponse(response => response.request().method() === "POST" && /\/api\/ai\/tools\/\d+\/execute\/$/.test(response.url()));
    await page.getByRole("dialog", { name: "Выполнить проверенное действие?" }).getByRole("button", { name: "Подтвердить", exact: true }).click();
    expect((await executed).status()).toBe(200);
    await expect(editor.getByText("Действие выполнено", { exact: true })).toBeVisible();
  }
  visits = (await session.list<any>("appointments")).filter(row => row.service === service.id);
  expect(visits).toHaveLength(2);
  for (const row of visits) expect(JSON.stringify(row.reserved_resources)).toContain("Booking Room");
  expect((await session.read(`appointments/${visit.id}`)).start_at).toContain("08:00:00");
  await page.screenshot({ path: info.outputPath("ai-confirmation.png"), fullPage: true });
});
