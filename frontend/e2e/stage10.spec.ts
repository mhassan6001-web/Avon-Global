import { expect, test } from "@playwright/test";

import { signIn, skipStartup } from "./helpers";

test.beforeEach(async ({ context }) => skipStartup(context));

test("a staff member adds their own task and posts an update", async ({ page }) => {
  await signIn(page, "procurement");
  await page.getByRole("link", { name: "Tasks" }).first().click();
  await page.getByRole("button", { name: "Add my task" }).click();
  const d = page.getByRole("dialog", { name: "Add my task" });
  await d.getByLabel("Task", { exact: true }).fill("E2E TEST follow up quotation");
  await d.getByRole("button", { name: "Save task" }).click();
  await page.getByRole("button", { name: "E2E TEST follow up quotation" }).first().click();
  const t = page.getByRole("dialog", { name: "E2E TEST follow up quotation" });
  await t.getByLabel("Update or question").fill("Started on this");
  await t.getByLabel("Status").selectOption("in_progress");
  await t.getByRole("button", { name: "Post update" }).click();
  await expect(t.getByText("Started on this")).toBeVisible();
});

test("a staff member submits a morning work plan", async ({ page }) => {
  await signIn(page, "logistics");
  await page.getByRole("link", { name: "Work reports" }).click();
  await page.getByLabel("Report", { exact: true }).fill("E2E TEST plan: check deliveries");
  await page.getByRole("button", { name: "Submit report" }).click();
  await expect(page.getByText("E2E TEST plan: check deliveries")).toBeVisible();
});
