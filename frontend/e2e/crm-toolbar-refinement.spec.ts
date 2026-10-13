import { expect, test, type Locator } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";
import { ru } from "../src/lib/i18n/ru";
import { en } from "../src/lib/i18n/en";
import { kk } from "../src/lib/i18n/kk";
import type { Client, Lead, TeamMember } from "../src/types";

test.beforeEach(() => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Disposable fixtures required");
  test.setTimeout(180_000);
});

async function withinViewport(locator: Locator) {
  expect(await locator.evaluate(element => {
    const box = element.getBoundingClientRect();
    return box.left >= 0 && box.top >= 0 && box.right <= innerWidth + 1 && box.bottom <= innerHeight + 1;
  })).toBe(true);
}

for (const [language, copy] of [["ru", ru], ["kk", kk], ["en", en]] as const) {
  test(`consistent toolbar, bounded menus and real pagination (${language})`, async ({ page, isMobile }, info) => {
    const session = await crmSession(page);
    const marker = `Refinement ${language} ${info.project.name}`;
    const members = (await session.list<TeamMember>("team/members")).filter(member => member.business === session.business && member.is_active);
    const teammate = members.find(member => member.user.id !== session.userId)!;
    const owner = members.find(member => member.user.id === session.userId)!;
    expect(teammate).toBeTruthy();
    expect(owner).toBeTruthy();
    const records: Lead[] = [];
    for (let index = 0; index < 13; index++) {
      const client = await session.create<Client>("clients", { full_name: `${marker} ${String(index).padStart(2, "0")}`, source: "manual" });
      records.push(await session.create<Lead>("leads", { client: client.id, source: "manual", message: marker, responsible_user: index < 12 ? session.userId : teammate.user.id }));
    }
    await page.evaluate(value => localStorage.setItem("ai_smb_language", value), language);
    const errors: string[] = [];
    page.on("pageerror", error => errors.push(error.message));
    const filterStyles: string[] = [];
    for (const kind of ["clients", "leads", "deals"] as const) {
      await page.goto(`/app/${kind}?search=${encodeURIComponent(marker)}`);
      const toolbar = page.getByTestId(`${kind}-unified-toolbar`);
      await expect(toolbar).toBeVisible();
      const filters = toolbar.getByRole("button", { name: new RegExp(`^${copy["crmFilters.filters"]}( \\d+)?$`) });
      await expect(filters).toHaveCount(1);
      filterStyles.push(await filters.evaluate(element => {
        const css = getComputedStyle(element);
        return [css.height, css.borderRadius, css.backgroundColor, css.fontSize].join("/");
      }));
      await expect(toolbar.getByRole("button", { name: copy["crmFilters.quick.all"], exact: true })).toHaveCount(0);
      await expect(toolbar.getByTestId(`${kind}-filter-status`)).toBeVisible();
      await expect(toolbar.getByTestId(`${kind}-filter-status`)).not.toHaveAttribute("role", "button");
      await withinViewport(toolbar);
      if (!isMobile) {
        const searchWidth = await toolbar.getByTestId(`${kind}-search-input`).evaluate(element => element.getBoundingClientRect().width);
        expect(searchWidth).toBeGreaterThanOrEqual(460);
      }
      await page.screenshot({ path: info.outputPath(`${kind}-${language}.png`) });
    }
    expect(new Set(filterStyles).size).toBe(1);

    for (const kind of ["clients", "leads"] as const) {
      await page.goto(`/app/${kind}?search=${encodeURIComponent(marker)}`);
      const footer = page.getByTestId("crm-pagination");
      await expect(footer).toBeVisible();
      const perPage = footer.getByRole("combobox", { name: copy["pagination.pageSizeAriaLabel"], exact: true });
      await perPage.click();
      const options = page.getByRole("listbox", { name: copy["pagination.pageSizeAriaLabel"], exact: true });
      await withinViewport(options);
      await options.getByRole("option", { name: "10", exact: true }).click();
      await expect(footer).toContainText(copy["pagination.visibleRange"].replace("{from}", "1").replace("{to}", "10").replace("{total}", "13"));
      await expect(footer.getByRole("button", { name: copy["pagination.previous"], exact: true })).toBeDisabled();
      await footer.getByRole("button", { name: copy["pagination.next"], exact: true }).click();
      await expect(footer).toContainText(copy["pagination.visibleRange"].replace("{from}", "11").replace("{to}", "13").replace("{total}", "13"));
      await expect(footer.getByRole("button", { name: copy["pagination.next"], exact: true })).toBeDisabled();
      await expect(page.getByTestId("action-feedback")).toHaveCount(0);
      await perPage.click();
      await page.getByRole("option", { name: "20", exact: true }).click();
      await expect(footer).toContainText(copy["pagination.total"].replace("{total}", "13"));
      await expect(footer.getByRole("navigation")).toHaveCount(0);
      if (!isMobile) expect(await footer.evaluate(element => element.getBoundingClientRect().height)).toBeLessThanOrEqual(50);
      await page.screenshot({ path: info.outputPath(`${kind}-pagination-${language}.png`) });
    }

    if (!isMobile) {
      await page.goto(`/app/leads?search=${encodeURIComponent(marker)}`);
      const row = page.getByTestId("lead-row-open").first();
      await expect(row).toBeVisible();
      const manager = row.getByRole("combobox", { name: copy["leads.responsible"], exact: true });
      await manager.click();
      const options = page.getByRole("listbox", { name: copy["leads.responsible"], exact: true });
      await withinViewport(options);
      await page.screenshot({ path: info.outputPath(`manager-${language}.png`) });
      const ownerOption = options.getByRole("option", { name: owner.user.full_name || owner.user.email, exact: true });
      const ownerOptionId = await ownerOption.getAttribute("id");
      await manager.press("Home");
      for (let index = 0; index < members.length && await manager.getAttribute("aria-activedescendant") !== ownerOptionId; index++) await manager.press("ArrowDown");
      await manager.press("Enter");
      await expect.poll(async () => (await session.read(`leads/${records.at(-1)!.id}`)).responsible_user).toBe(session.userId);
      await expect(page.getByTestId("crm-entity-drawer")).toHaveCount(0);
      await expect(manager).toBeFocused();
      await manager.click();
      await expect(options.getByRole("option", { name: copy["leads.withoutManager"], exact: true })).toHaveCount(0);
      await manager.press("Escape");
      await expect(options).toBeHidden();

      const trigger = row.getByTestId("lead-row-action-more");
      await trigger.focus();
      await trigger.press("Enter");
      const menu = page.getByTestId("lead-context-menu");
      await expect(menu).toBeVisible();
      await withinViewport(menu);
      await expect(menu.getByRole("menuitem").first()).toBeFocused();
      await page.keyboard.press("End");
      await expect(menu.getByRole("menuitem").last()).toBeFocused();
      await page.keyboard.press("Escape");
      await expect(menu).toBeHidden();
      await expect(trigger).toBeFocused();
      // Context click at the far right edge reproduces the supplied screenshot's overflow.
      const bounds = await row.boundingBox();
      await row.click({ button: "right", position: { x: bounds!.width - 5, y: 8 } });
      await expect(menu).toBeVisible();
      await withinViewport(menu);
      await page.screenshot({ path: info.outputPath(`right-edge-menu-${language}.png`) });
      await page.keyboard.press("Escape");
      await page.setViewportSize({ width: 1920, height: 900 });
      await page.screenshot({ path: info.outputPath(`wide-leads-${language}.png`) });
    }
    expect(errors).toEqual([]);
  });
}
