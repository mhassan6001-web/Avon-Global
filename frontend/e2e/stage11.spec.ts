import { expect, test } from "@playwright/test";

import { signIn, skipStartup } from "./helpers";

test.beforeEach(async ({ context }) => skipStartup(context));

test("JARVIS briefs from recorded data and prepares a task that needs confirmation", async ({
  page,
}) => {
  await signIn(page, "director");
  await page.getByRole("link", { name: "JARVIS" }).first().click();
  await expect(page.getByRole("heading", { name: "JARVIS", level: 1 })).toBeVisible();
  await expect(page.getByText("from recorded data only", { exact: false })).toBeVisible();
  await expect(page.getByText("Nothing is waiting for your decision.")).toBeVisible();

  await page.getByLabel("Ask JARVIS").fill("Create task: E2E TEST call the clearing agent");
  await page.getByRole("button", { name: "Ask", exact: true }).click();
  const card = page.getByRole("group", { name: "Prepared action" });
  await expect(card.getByText("Needs your confirmation")).toBeVisible();
  await card.getByRole("button", { name: "Confirm" }).click();
  await expect(card.getByText("executed")).toBeVisible();

  await page.getByRole("link", { name: "Tasks" }).first().click();
  await expect(page.getByText("E2E TEST call the clearing agent")).toBeVisible();
  await expect(page.getByText(/prepared by JARVIS/).first()).toBeVisible();
});

test("JARVIS is not available to departments without access", async ({ page }) => {
  await signIn(page, "finance");
  await expect(page.getByRole("link", { name: "JARVIS" })).toHaveCount(0);
});
