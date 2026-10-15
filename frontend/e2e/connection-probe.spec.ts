import { expect, test } from "@playwright/test";

test("public readiness is independent of credentials and a concurrent session change", async ({ page }) => {
  await page.goto("/e2e/fixtures/state-behavior.html");
  await expect(page.getByTestId("draft")).toBeVisible();
  let release = () => {};
  const pending = new Promise<void>(resolve => { release = resolve; });
  let requested = false;
  let authorization: string | undefined;
  await page.route("**/ready/", async route => {
    authorization = route.request().headers().authorization;
    requested = true;
    await pending;
    await route.fulfill({ json: { status: "ok" } });
  });
  const probe = page.evaluate(async () => {
    const storagePath = "/src/lib/storage.ts";
    const connectivityPath = "/src/api/connectivity.ts";
    (await import(storagePath)).tokenStorage.setAccess("expired-test-credential");
    try {
      await (await import(connectivityPath)).checkServiceConnection(new AbortController().signal);
      return "ok";
    } catch { return "failed"; }
  });
  await expect.poll(() => requested).toBe(true);
  await page.evaluate(async () => {
    const storagePath = "/src/lib/storage.ts";
    (await import(storagePath)).tokenStorage.clear();
  });
  release();
  expect(await probe).toBe("ok");
  expect(authorization).toBeUndefined();
});
