import { expect, test } from "@playwright/test";
import { spawnSync } from "node:child_process";
import path from "node:path";

const api = process.env.E2E_API_BASE_URL || "http://127.0.0.1:8000";

test("password reset link changes credentials once and rejects token replay", async ({ page }) => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Synthetic reset token is restricted to the isolated quality-gate database");
  test.setTimeout(90_000);
  expect(process.env.DATABASE_URL).toMatch(/zani-quality-gate-[^/]+\/gate\.sqlite3$/);
  expect(process.env.E2E_PYTHON).toBeTruthy();
  const email = `pilot-reset-${Date.now()}@example.com`;
  const password = "PilotResetInitial928!";
  const replacement = "PilotResetChanged928!";
  const created = await page.request.post(`${api}/api/auth/signup/owner/`, {
    data: { email, password, full_name: "Pilot reset owner", business_name: "Reset fixture", phone: "+77770009944" },
  });
  expect(created.status()).toBe(201);
  const account = await created.json();
  // Use Django's real token generator in the isolated DB. This proves link/UI
  // consumption and session revocation, not delivery by an external mail server.
  const fixture = spawnSync(process.env.E2E_PYTHON!, ["manage.py", "shell", "-c", [
    "import os,json",
    "from apps.accounts.models import User",
    "from django.contrib.auth.tokens import default_token_generator",
    "from django.utils.http import urlsafe_base64_encode",
    "from django.utils.encoding import force_bytes",
    "user=User.objects.get(email=os.environ['PILOT_RESET_EMAIL'])",
    "print(json.dumps({'uid':urlsafe_base64_encode(force_bytes(user.pk)),'token':default_token_generator.make_token(user)}))",
  ].join("; ")], {
    cwd: path.resolve(process.cwd(), ".."), env: { ...process.env, PILOT_RESET_EMAIL: email }, encoding: "utf8", timeout: 30_000,
  });
  expect(fixture.status, fixture.stderr || String(fixture.error || "")).toBe(0);
  const reset = JSON.parse(fixture.stdout.trim().split(/\r?\n/).at(-1)!);
  await page.context().clearCookies();
  await page.goto(`/reset-password/${reset.uid}/${reset.token}`);
  await page.locator('form input[name="password"]').fill(replacement);
  await page.locator('form input[name="password_confirm"]').fill(replacement);
  const confirmation = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/api/auth/password-reset/confirm/"));
  await page.locator('form button[type="submit"]').click();
  expect((await confirmation).ok()).toBeTruthy();
  await expect(page).toHaveURL(/\/login$/);
  const oldSession = await page.request.get(`${api}/api/auth/me/`, { headers: { Authorization: `Bearer ${account.access}` } });
  expect(oldSession.status()).toBe(401);
  const oldPassword = await page.request.post(`${api}/api/auth/token/`, { data: { email, password } });
  expect(oldPassword.status()).toBe(401);
  const replay = await page.request.post(`${api}/api/auth/password-reset/confirm/`, { data: { ...reset, password: "PilotReplayForbidden928!" } });
  expect(replay.status()).toBe(400);
  await page.locator('form input[type="email"]').fill(email);
  await page.locator('form input[type="password"]').fill(replacement);
  const login = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/api/auth/token/"));
  await page.locator('form button[type="submit"]').click();
  expect((await login).ok()).toBeTruthy();
  await expect(page).toHaveURL(/\/app/);
});
