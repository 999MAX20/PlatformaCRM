import { expect, test } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";
import type { TeamMember } from "../src/types";

test.beforeEach(() => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Disposable branch grants required");
  test.setTimeout(150_000);
});

for (const [locale, copy] of Object.entries({ ru, kk, en })) {
  test(`branch grants match owner and administrator scope ${locale}`, async ({ page, browser }, info) => {
    const owner = await crmSession(page);
    const members = await owner.list<TeamMember>("team/members");
    const admin = members.find(member => member.user.email === "business_administrator@example.com")!;
    const target = members.find(member => member.user.email === "business_operator@example.com")!;
    const first = await owner.create<{ id: number; name: string }>("branches", { name: `QA024 A ${locale} ${info.project.name}`, address: "Synthetic A" });
    const second = await owner.create<{ id: number; name: string }>("branches", { name: `QA024 B ${locale} ${info.project.name}`, address: "Synthetic B" });
    const grant = (member: number, branch_ids: number[], all_branches = false) => owner.action("branches/member-access", { member, branch_ids, all_branches });
    await grant(admin.id, [first.id]);
    await grant(target.id, [first.id]);
    async function open(editor: typeof page) {
      await editor.goto("/app/settings#team-access");
      await editor.locator("#team-access").getByRole("button").filter({ hasText: target.user.email }).click();
      const form = editor.getByTestId("team-branch-access");
      await expect(form).toBeVisible();
      return form;
    }
    await page.evaluate(value => localStorage.setItem("ai_smb_language", value), locale);
    const ownerForm = await open(page);
    await ownerForm.getByRole("checkbox", { name: copy["branches.allFuture"], exact: true }).check();
    await ownerForm.getByRole("button", { name: copy["common.save"], exact: true }).click();
    await expect.poll(async () => (await owner.read(`team/members/${target.id}`)).branch_access.all_branches).toBe(true);
    await grant(target.id, [first.id]);

    const adminContext = await browser.newContext({ baseURL: info.project.use.baseURL,
      viewport: info.project.use.viewport, isMobile: info.project.use.isMobile,
      deviceScaleFactor: info.project.use.deviceScaleFactor, hasTouch: info.project.use.hasTouch });
    try {
      const editor = await adminContext.newPage();
      await crmSession(editor, admin.user.email);
      await editor.evaluate(value => localStorage.setItem("ai_smb_language", value), locale);
      let form = await open(editor);
      await expect(form.getByRole("checkbox", { name: copy["branches.allFuture"], exact: true })).toBeDisabled();
      await expect(form.getByRole("checkbox", { name: second.name, exact: true })).toHaveCount(0);
      await expect(form.getByText(copy["branches.futureGrantRestricted"], { exact: true })).toBeVisible();
      const selected = form.getByRole("checkbox", { name: first.name, exact: true });
      await selected.focus();
      await selected.press("Space");
      await expect(selected).not.toBeChecked();
      await editor.route("**/api/branches/member-access/", route => route.request().method() === "POST"
        ? route.fulfill({ status: 503, json: { detail: "Synthetic temporary failure" } }) : route.continue());
      await form.getByRole("button", { name: copy["common.save"], exact: true }).click();
      await expect(form.getByRole("alert")).toBeVisible();
      await expect(selected).not.toBeChecked();
      await editor.unroute("**/api/branches/member-access/");
      await form.getByRole("button", { name: copy["common.save"], exact: true }).click();
      await expect.poll(async () => (await owner.read(`team/members/${target.id}`)).branch_access.branch_ids).toEqual([]);
      await selected.check();
      await form.getByRole("button", { name: copy["common.save"], exact: true }).click();
      await expect.poll(async () => (await owner.read(`team/members/${target.id}`)).branch_access.branch_ids).toEqual([first.id]);
      await editor.screenshot({ path: info.outputPath(`limited-admin-${locale}.png`), fullPage: true });
      expect(await form.evaluate(element => element.scrollWidth <= element.clientWidth + 1)).toBeTruthy();

      await grant(target.id, [second.id]);
      await editor.reload();
      form = await open(editor);
      await expect(form.getByText(copy["branches.grantOutsideScope"], { exact: true })).toBeVisible();
      await expect(form.getByRole("button", { name: copy["common.save"], exact: true })).toBeDisabled();
      await editor.screenshot({ path: info.outputPath(`outside-scope-${locale}.png`), fullPage: true });
      await grant(admin.id, [], true);
      await editor.reload();
      form = await open(editor);
      await form.getByRole("checkbox", { name: copy["branches.allFuture"], exact: true }).check();
      await form.getByRole("button", { name: copy["common.save"], exact: true }).click();
      await expect.poll(async () => (await owner.read(`team/members/${target.id}`)).branch_access.all_branches).toBe(true);
      await editor.reload();
      form = await open(editor);
      await expect(form.getByRole("checkbox", { name: copy["branches.allFuture"], exact: true })).toBeChecked();
    } finally {
      await adminContext.close();
    }
  });
}
