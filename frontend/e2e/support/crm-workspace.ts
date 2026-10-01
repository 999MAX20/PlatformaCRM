import { expect, type Page } from "@playwright/test";
import type { Client, Lead, Pipeline, PipelineStage } from "../../src/types";

const api = process.env.E2E_API_BASE_URL || "http://127.0.0.1:8000";

export async function crmSession(page: Page, email = "business_owner@example.com") {
  await page.goto("/login");
  await page.locator('form input[type="email"]').fill(email);
  await page.locator('form input[type="password"]').fill(process.env.E2E_PASSWORD || "ZaniTest123!");
  const pending = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/api/auth/token/"));
  await page.locator('form button[type="submit"]').click();
  const login = await pending;
  expect(login.ok()).toBeTruthy();
  const headers = { Authorization: `Bearer ${(await login.json()).access}` };
  const me = await page.request.get(`${api}/api/auth/me/`, { headers });
  expect(me.ok()).toBeTruthy();
  const profile = await me.json();
  await expect(page.getByTestId("header-account-link")).toBeVisible();
  return {
    headers, business: profile.businesses[0].id as number, userId: profile.id as number,
    async create<T>(resource: string, data: Record<string, unknown>): Promise<T> {
      const response = await page.request.post(`${api}/api/${resource}/`, { headers, data: { business: profile.businesses[0].id, ...data } });
      expect(response.status(), await response.text()).toBe(201);
      return response.json();
    },
    async list<T>(resource: string): Promise<T[]> {
      const response = await page.request.get(`${api}/api/${resource}/`, { headers });
      expect(response.ok(), await response.text()).toBeTruthy();
      const data = await response.json();
      return data.results || data;
    },
    async action(resource: string, data: Record<string, unknown> = {}) {
      const response = await page.request.post(`${api}/api/${resource}/`, { headers, data });
      expect(response.ok(), await response.text()).toBeTruthy();
      return response.json();
    },
    async read(resource: string, params?: Record<string, string | number>) {
      const response = await page.request.get(`${api}/api/${resource}/`, { headers, params });
      expect(response.ok(), await response.text()).toBeTruthy();
      return response.json();
    },
  };
}

export async function representativeWorkspace(page: Page) {
  const session = await crmSession(page);
  const pipelines = await session.list<Pipeline>("pipelines");
  const pipeline = pipelines.find(item => item.is_default) || pipelines[0];
  const stages = (await session.list<PipelineStage>("pipeline-stages"))
    .filter(item => item.pipeline === pipeline.id && item.is_active).sort((a, b) => a.order - b.order);
  const names = ["Анна Смирнова", "Данияр Ахметов", "Мария Ким", "Алексей Волков", "Алия Садыкова", "Ирина Белова", "Тимур Омаров", "Елена Петрова", "Олег Соколов", "София Ли", "Ольга Николаева", "Руслан Каримов"];
  const clients: Client[] = [];
  const leads: Lead[] = [];
  for (const [index, full_name] of names.entries()) {
    const client = await session.create<Client>("clients", { full_name, source: index % 3 ? "website" : "manual", email: `reference-${index}@example.invalid` });
    clients.push(client);
    leads.push(await session.create<Lead>("leads", { client: client.id, source: client.source, message: index % 2 ? "Запись на приём" : "Консультация", responsible_user: session.userId }));
    if (index % 3 === 1) await session.action(`leads/${leads[index].id}/take-in-work`);
    if (index % 3 !== 0) await session.create("tasks", { client: client.id, lead: leads[index].id, title: "Позвонить клиенту", assignee: session.userId, due_at: index % 2 ? "2026-10-03T09:00:00Z" : null });
  }
  for (const stage of stages.filter(item => !item.is_won && !item.is_lost)) {
    for (let index = 0; index < 7; index++) {
      const deal = await session.create<{ id: number }>("deals", { client: clients[index].id, pipeline: pipeline.id, stage: stage.id, title: index % 2 ? "Повторная запись" : "Первичная консультация", amount: String(90000 + index * 10000), owner: session.userId, source: "manual" });
      if (index % 2 === 0) await session.create("tasks", { client: clients[index].id, deal: deal.id, title: "Подтвердить время", due_at: "2026-10-03T09:00:00Z", assignee: session.userId });
    }
  }
  return { ...session, clients, leads, pipeline, stages };
}
