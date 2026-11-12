import { expect, test } from "@playwright/test";

import { signIn, skipStartup } from "./helpers";

test.beforeEach(async ({ context }) => skipStartup(context));

test("HR adds an employee and a configured pay component; payroll stays restricted", async ({
  page,
}) => {
  await signIn(page, "hr_admin");
  await page.getByRole("link", { name: "HR & Payroll" }).first().click();
  await page.getByRole("button", { name: "New employee" }).click();
  const d = page.getByRole("dialog", { name: "New employee" });
  await d.getByLabel("Full name").fill("E2E TEST Employee");
  await d.getByLabel("Job title").fill("Driver");
  await d.getByLabel("Start date").fill("2026-01-05");
  await d.getByRole("button", { name: "Create employee" }).click();
  await expect(page.getByText("E2E TEST Employee")).toBeVisible();
  await expect(page.getByText(/^EMP-\d{5}$/).first()).toBeVisible();

  await page.getByRole("radio", { name: "Payroll" }).click();
  await page.getByRole("button", { name: "Add", exact: true }).click();
  const c = page.getByRole("dialog", { name: "Add pay component" });
  await c.getByLabel("Code").fill("E2E-TAX");
  await c.getByLabel("Name").fill("E2E test tax");
  await c.getByLabel("Method").selectOption("bands");
  await c.getByLabel(/Bands, one per line/).fill("0,100000,0\n100000,,25");
  await c.getByLabel("Source of these figures").fill("E2E test values only");
  await c.getByRole("button", { name: "Add component" }).click();
  await expect(page.getByText("E2E test tax · Deduction · 2 bands")).toBeVisible();
});

test("staff without an HR link see a clear message on My HR", async ({ page }) => {
  await signIn(page, "procurement");
  await page.getByRole("link", { name: "My HR" }).click();
  await expect(page.getByText(/not linked to an employee record/)).toBeVisible();
  await page.goto("/hr");
  await expect(
    page.getByText("You do not have permission to perform this action.").first(),
  ).toBeVisible();
});
