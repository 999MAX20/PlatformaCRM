import { expect, test, type Page } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";

async function renderedFonts(page: Page, selector: string) {
  const session = await page.context().newCDPSession(page);
  try {
    await session.send("DOM.enable");
    await session.send("CSS.enable");
    const { root } = await session.send("DOM.getDocument");
    const { nodeId } = await session.send("DOM.querySelector", { nodeId: root.nodeId, selector });
    return (await session.send("CSS.getPlatformFontsForNode", { nodeId })).fonts;
  } finally {
    await session.detach();
  }
}

test("Kazakh headings and alphabet use one bundled family at every UI weight", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("ai_smb_language", "kk"));
  await page.goto("/forgot-password");
  await expect(page.getByRole("heading", { name: "Құпиясөзді қалпына келтіру", exact: true })).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("lang", "kk");
  await page.evaluate(() => document.fonts.ready);
  const headingFonts = await renderedFonts(page, "h1");
  expect(headingFonts.length).toBeGreaterThan(0);
  expect(headingFonts.every(font => font.isCustomFont && font.familyName.startsWith("Noto Sans"))).toBe(true);
  await page.screenshot({ path: test.info().outputPath("kazakh-password-recovery.png"), fullPage: true });

  for (const weight of [400, 500, 600, 700, 800]) {
    await page.evaluate(async value => {
      document.getElementById("kazakh-font-probe")?.remove();
      const probe = document.createElement("p");
      probe.id = "kazakh-font-probe";
      probe.textContent = "Әә Ғғ Ққ Ңң Өө Ұұ Үү Һһ Іі Құпиясөз 0123456789";
      probe.style.fontWeight = String(value);
      document.body.append(probe);
      await document.fonts.load(`${value} 16px "Noto Sans Variable"`, probe.textContent);
      await document.fonts.ready;
    }, weight);
    const fonts = await renderedFonts(page, "#kazakh-font-probe");
    expect(fonts.length).toBeGreaterThan(0);
    expect(fonts.every(font => font.isCustomFont && font.familyName.startsWith("Noto Sans")), `Unexpected fallback at weight ${weight}`).toBe(true);
  }
});

test("switching locale updates typography without clearing the login draft", async ({ page }) => {
  await page.goto("/login");
  const email = page.locator('input[type="email"]');
  await email.fill("font-draft@example.invalid");
  for (const locale of ["kk", "ru", "en", "kk"]) {
    await page.getByRole("combobox").click();
    await page.getByRole("option", { name: locale.toUpperCase(), exact: true }).click();
    await expect(page.locator("html")).toHaveAttribute("lang", locale);
    await expect(email).toHaveValue("font-draft@example.invalid");
    const family = await page.locator("h2").evaluate(element => getComputedStyle(element).fontFamily);
    expect(family.startsWith(locale === "kk" ? '"Noto Sans Variable"' : '"Manrope Variable"')).toBe(true);
  }
});

test("authenticated CRM also uses bundled Kazakh typography", async ({ page }) => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Requires disposable synthetic account");
  await page.addInitScript(() => localStorage.setItem("ai_smb_language", "kk"));
  await crmSession(page);
  await page.goto("/app/clients");
  await expect(page.locator("html")).toHaveAttribute("lang", "kk");
  const filters = page.getByRole("button", { name: "Сүзгілер", exact: true });
  await expect(filters).toBeVisible();
  await filters.evaluate(element => { element.id = "kazakh-crm-font-target"; });
  await page.evaluate(() => document.fonts.ready);
  const fonts = await renderedFonts(page, "#kazakh-crm-font-target");
  expect(fonts.length).toBeGreaterThan(0);
  expect(fonts.every(font => font.isCustomFont && font.familyName.startsWith("Noto Sans"))).toBe(true);
  await page.screenshot({ path: test.info().outputPath("kazakh-clients.png"), fullPage: true });
});
