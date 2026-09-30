import { expect, type APIRequestContext } from "@playwright/test";

// Restore only the preferences these isolated tests own, even after an assertion
// fails, so another viewport does not inherit a changed language/start page.
export async function resetAccountPreferences(request: APIRequestContext) {
  const login = await request.post("/api/auth/token/", {
    data: { email: process.env.E2E_OWNER_EMAIL || "business_owner@example.com", password: process.env.E2E_PASSWORD || "ZaniTest123!" },
  });
  expect(login.ok()).toBeTruthy();
  const { access } = await login.json();
  const result = await request.patch("/api/auth/me/", {
    headers: { Authorization: `Bearer ${access}` },
    data: { preferences: { language: "ru", start_page: "dashboard" } },
  });
  expect(result.ok()).toBeTruthy();
}
