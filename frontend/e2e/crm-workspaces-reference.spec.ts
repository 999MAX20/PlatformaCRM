import { expect, test } from "@playwright/test";
import { crmSession, representativeWorkspace } from "./support/crm-workspace";

test("the three real CRM workspaces fill the area below the header without outer cards", async ({ page }, testInfo) => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Requires disposable synthetic CRM data");
  test.skip(testInfo.project.name !== "desktop-chromium", "Reference viewport; other projects have responsive coverage below");
  test.setTimeout(180_000);
  await page.setViewportSize({ width: 1672, height: 941 });
  await representativeWorkspace(page);
  const boxes: Array<{ route: string; x: number; y: number; width: number; height: number }> = [];
  for (const route of ["leads", "deals", "clients"]) {
    await page.goto(`/app/${route}`);
    const workspace = page.getByTestId(`${route}-workspace-ready`);
    await expect(workspace).toBeVisible();
    await page.evaluate(() => document.fonts.ready);
    const surface = workspace.locator("section").first();
    await expect(surface).toBeVisible();
    const box = await surface.boundingBox();
    expect(box).toBeTruthy();
    boxes.push({ route, ...box! });
    await page.screenshot({ path: testInfo.outputPath(`${route}.png`), animations: "disabled" });
  }
  await testInfo.attach("workspace-geometry", { body: JSON.stringify(boxes, null, 2), contentType: "application/json" });
  for (const box of boxes) {
    expect(Math.abs(box.y + box.height - 941)).toBeLessThanOrEqual(2);
    expect(Math.abs(box.x - 64)).toBeLessThanOrEqual(2);
    expect(Math.abs(box.y - 57)).toBeLessThanOrEqual(2);
    expect(Math.abs(box.width - (1672 - 64))).toBeLessThanOrEqual(2);
    expect(Math.abs(box.x - boxes[0].x)).toBeLessThanOrEqual(2);
    expect(Math.abs(box.y - boxes[0].y)).toBeLessThanOrEqual(2);
    expect(Math.abs(box.width - boxes[0].width)).toBeLessThanOrEqual(2);
  }
});

for (const route of ["leads", "clients"] as const) {
  test(`${route} search, filters, columns and keyboard opening use real records`, async ({ page }, testInfo) => {
    test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Requires disposable data");
    test.setTimeout(90_000);
    const session = await crmSession(page);
    const marker = `Workspace ${route} ${testInfo.project.name} ${Date.now()}`;
    const client = await session.create<{ id: number }>("clients", { full_name: marker, source: "manual" });
    if (route === "leads") await session.create("leads", { client: client.id, source: "manual", message: marker });
    await page.goto(`/app/${route}`);
    const workspace = page.getByTestId(`${route}-workspace-ready`);
    await expect(workspace).toBeVisible();
    const search = page.getByTestId(`${route}-search-input`);
    await search.fill(marker);
    const direct = await session.read(route, { [route === "clients" ? "q" : "search"]: marker });
    expect(direct.count).toBe(1);
    await expect(workspace.getByText(marker, { exact: true }).filter({ visible: true }).first()).toBeVisible();
    const filterButton = workspace.getByRole("button", { name: /^Фильтры/ });
    await filterButton.click();
    const filterDialog = page.getByRole("dialog", { name: "Фильтры", exact: true });
    await expect(filterDialog).toBeVisible();
    const bounds = await filterDialog.boundingBox();
    expect(bounds!.x).toBeGreaterThanOrEqual(0);
    expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(page.viewportSize()!.width);
    await filterDialog.getByRole("combobox", { name: "Источник", exact: true }).click();
    await filterDialog.getByRole("option", { name: "Сайт", exact: true }).click();
    await page.keyboard.press("Escape");
    await expect(filterDialog).toBeHidden();
    await expect(filterButton).toBeFocused();
    await expect(workspace.getByText(marker, { exact: true })).toHaveCount(0);
    await workspace.getByRole("button", { name: /^Источник:/ }).click();
    await expect(workspace.getByText(marker, { exact: true }).filter({ visible: true }).first()).toBeVisible();

    const columns = workspace.getByRole("button", { name: /^(Колонки|Столбцы)$/ });
    await columns.click();
    const columnsDialog = page.getByRole("dialog", { name: /^(Колонки|Столбцы)$/ });
    const managerColumn = columnsDialog.getByRole("checkbox", { name: "Менеджер", exact: true });
    await managerColumn.uncheck();
    await page.keyboard.press("Escape");
    await page.reload();
    await expect(workspace).toBeVisible();
    await columns.click();
    await expect(managerColumn).not.toBeChecked();
    await managerColumn.check();
    await page.keyboard.press("Escape");
    await search.fill(marker);
    await expect(workspace.getByText(marker, { exact: true }).filter({ visible: true }).first()).toBeVisible();

    if (testInfo.project.name === "desktop-chromium") {
      if (route === "clients") {
        const row = workspace.getByRole("row").filter({ hasText: marker });
        const checkbox = row.getByRole("checkbox");
        await checkbox.focus();
        await page.keyboard.press("Space");
        await expect(checkbox).toBeChecked();
        await expect(page.getByRole("dialog")).toHaveCount(0);
        await row.focus();
        await page.keyboard.press("Enter");
      } else {
        const row = workspace.getByTestId("lead-row-open").filter({ hasText: marker });
        await row.getByTestId("lead-row-keyboard-open").focus();
        await page.keyboard.press("Enter");
      }
      await expect(page.getByRole("dialog").first()).toBeVisible();
      await page.keyboard.press("Escape");
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
  });
}

for (const route of ["leads", "deals", "clients"] as const) {
  test(`${route} recovers a failed list request without losing its workspace`, async ({ page }) => {
    test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Requires disposable data");
    test.setTimeout(60_000);
    await crmSession(page);
    let failing = true;
    const endpoint = route === "deals" ? "/api/deals/board/" : `/api/${route}/`;
    await page.route((url) => url.pathname === endpoint, async (request) => {
      if (failing) await request.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "Workspace recovery test" }) });
      else await request.continue();
    });
    await page.goto(`/app/${route}`);
    const retry = page.getByRole("button", { name: "Повторить", exact: true });
    await expect(retry).toBeVisible({ timeout: 25_000 });
    failing = false;
    await retry.click();
    await expect(page.getByTestId(`${route}-workspace-ready`)).toBeVisible();
    await expect(retry).toBeHidden();
  });
}

test("responsive workspaces keep actions and pagination reachable", async ({ page }, testInfo) => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Requires disposable data");
  test.setTimeout(90_000);
  await crmSession(page);
  for (const route of ["leads", "clients", "deals"]) {
    await page.goto(`/app/${route}`);
    const workspace = page.getByTestId(`${route}-workspace-ready`);
    await expect(workspace).toBeVisible();
    await expect(page.getByTestId(`${route}-search-input`)).toBeInViewport();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
    if (route !== "deals") {
      const footer = workspace.getByTestId("crm-pagination");
      await expect(footer).toBeInViewport();
      const footerBox = await footer.boundingBox();
      if (testInfo.project.name === "mobile-chromium") expect(footerBox!.y + footerBox!.height).toBeLessThan(page.viewportSize()!.height - 65);
    }
    await page.screenshot({ path: testInfo.outputPath(`${route}-${testInfo.project.name}.png`), animations: "disabled" });
  }
});
