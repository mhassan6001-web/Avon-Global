import { expect, test } from "@playwright/test";

import { signIn, skipStartup } from "./helpers";

test.beforeEach(async ({ context }) => skipStartup(context));

test("the sign-in page shows the AVEN GLOBAL logo and the app is installable", async ({
  page,
  request,
}) => {
  await page.goto("/sign-in");
  await expect(page.getByRole("img", { name: "AVEN GLOBAL" })).toBeVisible();
  const manifest = await request.get("/manifest.webmanifest");
  expect(manifest.ok()).toBeTruthy();
  expect((await manifest.json()).name).toBe("AVEN GLOBAL");
  expect((await request.get("/sw.js")).ok()).toBeTruthy();
});

test("staff download the letterhead and see it in the document register", async ({ page }) => {
  await signIn(page, "logistics");
  await page.getByRole("link", { name: "Documents", exact: true }).first().click();
  await expect(page.getByRole("heading", { name: "Documents", level: 1 })).toBeVisible();
  await expect(page.getByRole("link", { name: /Trial balance/ })).toHaveCount(0);
  const download = page.waitForEvent("download");
  await page.getByRole("link", { name: /Letterhead \(Word\)/ }).click();
  expect((await download).suggestedFilename()).toMatch(/^AVEN-GLOBAL-letterhead-v\d+\.docx$/);
  await page.reload();
  await expect(page.getByRole("cell", { name: /AVEN-GLOBAL-letterhead/ }).first()).toBeVisible();
});
