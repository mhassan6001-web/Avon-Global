import { expect, test } from "@playwright/test";

import { signIn, skipStartup } from "./helpers";

test.beforeEach(async ({ context }) => skipStartup(context));

test("finance: set up books, issue an invoice, see a balanced trial balance", async ({ page }) => {
  const year = new Date().getFullYear();
  await signIn(page, "finance");
  await page.getByRole("link", { name: "Finance" }).first().click();
  await expect(page.getByText(/Setup needed before posting/)).toBeVisible();
  await expect(page.getByText("Not yet reviewed by an accountant")).toBeVisible();

  await page.getByRole("link", { name: "Setup", exact: true }).click();
  for (const [code, name, kind] of [
    ["E1000", "E2E TEST Bank", "bank"],
    ["E1100", "E2E TEST Debtors", "receivable"],
    ["E4000", "E2E TEST Sales", "revenue"],
  ] as const) {
    await page.getByLabel("Account code").fill(code);
    await page.getByLabel("Account name").fill(name);
    await page.getByLabel("Kind").selectOption(kind);
    await page.getByRole("button", { name: "Add account" }).click();
    await expect(page.getByRole("cell", { name, exact: true })).toBeVisible();
  }
  await page.getByLabel("Debtors control").selectOption({ label: "E1100 E2E TEST Debtors" });
  await page.getByRole("button", { name: "Save control accounts" }).click();
  await page.getByLabel("Period name").fill(`E2E FY${year}`);
  await page.getByLabel("Starts").fill(`${year}-01-01`);
  await page.getByLabel("Ends").fill(`${year}-12-31`);
  await page.getByRole("button", { name: "Add period" }).click();
  await expect(page.getByText(`E2E FY${year}`)).toBeVisible();

  await page.getByRole("link", { name: "Sales & receipts" }).click();
  await page.getByRole("button", { name: "New invoice" }).click();
  const dialog = page.getByRole("dialog", { name: "New invoice" });
  await dialog.getByLabel("Customer", { exact: true }).selectOption({ index: 1 });
  await dialog.getByLabel("Description 1").fill("E2E consulting");
  await dialog.getByLabel("Unit price 1").fill("1500.50");
  await dialog.getByLabel("Revenue account 1").selectOption({ label: "E4000 E2E TEST Sales" });
  await dialog.getByRole("button", { name: "Save draft" }).click();
  await expect(page.getByRole("cell", { name: "Draft", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Issue", exact: true }).click();
  await expect(page.getByText(`INV-${year}-00001`).first()).toBeVisible();
  await expect(page.getByText("MWK 1,500.50").first()).toBeVisible();

  await page.getByRole("link", { name: "Reports", exact: true }).click();
  await expect(page.getByText("Balanced", { exact: true })).toBeVisible();
  await expect(page.getByRole("cell", { name: "E1100 E2E TEST Debtors" }).first()).toBeVisible();
});

test("finance is invisible and refused for other departments", async ({ page }) => {
  await signIn(page, "logistics");
  await expect(page.getByRole("link", { name: "Finance" })).toHaveCount(0);
  await page.goto("/finance/invoices");
  await expect(
    page.getByText("You do not have permission to perform this action.").first(),
  ).toBeVisible();
});
