import { expect, test } from "@playwright/test";

import { signIn, skipStartup } from "./helpers";

test.beforeEach(async ({ context }) => skipStartup(context));

test("staff prepare a quotation; it needs approval by default and downloads as a draft", async ({
  page,
}) => {
  await signIn(page, "business_development");
  await page.goto("/crm");
  await page.getByRole("button", { name: "New customer" }).click();
  const c = page.getByRole("dialog", { name: "New customer" });
  await c.getByLabel("Name").fill("E2E TEST Quote Customer");
  await c.getByRole("button", { name: "Create customer" }).click();
  await expect(
    page.getByRole("heading", { name: "E2E TEST Quote Customer", level: 1 }),
  ).toBeVisible();

  await page.goto("/crm/quotations");
  await expect(page.getByRole("heading", { name: "Quotations", level: 1 })).toBeVisible();
  await page.getByRole("button", { name: "New quotation" }).click();
  const d = page.getByRole("dialog", { name: "New quotation" });
  await d
    .getByLabel("Customer", { exact: true })
    .selectOption({ label: "E2E TEST Quote Customer" });
  await d.getByLabel("Subject").fill("E2E TEST stationery");
  await d.getByLabel("Item 1", { exact: true }).fill("A4 paper");
  await d.getByLabel("Quantity 1", { exact: true }).fill("10");
  await d.getByLabel("Unit price 1", { exact: true }).fill("6500");
  await d.getByRole("button", { name: "Save draft" }).click();
  const row = page.getByRole("row", { name: /E2E TEST stationery/ });
  await expect(row.getByText("MWK 65,000.00")).toBeVisible();
  const download = page.waitForEvent("download");
  await row.getByRole("link", { name: "Quotation draft as PDF" }).click();
  expect((await download).suggestedFilename()).toMatch(/^DRAFT-v1\.pdf$/);

  await row.getByRole("button", { name: "Issue" }).click();
  await expect(row.getByText("Waiting for approval")).toBeVisible();
});

test("the Director sees the approval rules and the sole-approver notice", async ({ page }) => {
  await signIn(page, "director");
  await page.getByRole("link", { name: "Approvals" }).first().click();
  await expect(page.getByRole("heading", { name: "Approval rules" })).toBeVisible();
  await expect(page.getByText("Quotations prepared by staff")).toBeVisible();
  await expect(page.getByText("You are the only approver").first()).toBeVisible();
  await expect(page.getByText("E2E TEST stationery", { exact: false }).first()).toBeVisible();
});
