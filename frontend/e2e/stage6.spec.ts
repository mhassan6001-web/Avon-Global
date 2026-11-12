import { expect, test } from "@playwright/test";

import { signIn, skipStartup } from "./helpers";

test.beforeEach(async ({ context }) => skipStartup(context));

test("procurement: verified supplier, quotation comparison, approval request", async ({ page }) => {
  const stamp = Date.now();
  const supplier = `E2E TEST Supplier ${stamp}`;
  await signIn(page, "procurement");
  await page.getByRole("link", { name: "Procurement" }).first().click();
  await page.getByRole("link", { name: "Suppliers" }).click();

  await page.getByRole("button", { name: "New supplier" }).click();
  const sd = page.getByRole("dialog", { name: "New supplier" });
  await sd.getByLabel("Supplier name").fill(supplier);
  await sd.getByRole("button", { name: "Create supplier" }).click();
  await expect(page.getByRole("heading", { name: supplier, level: 1 })).toBeVisible();

  // Bank details: masked for Procurement, change goes for approval.
  await page.getByRole("button", { name: "Request bank-detail change" }).click();
  const bank = page.getByRole("dialog", { name: "Request bank-detail change" });
  await bank.getByLabel("Bank", { exact: true }).fill("E2E TEST Bank");
  await bank.getByLabel("Account name").fill("E2E TEST Account");
  await bank.getByLabel("Account number").fill("5550001234");
  await bank.getByLabel("Reason and how it was confirmed").fill("Confirmed by phone on file");
  await bank.getByRole("button", { name: "Send for approval" }).click();
  await expect(page.getByText(/•••• 1234/)).toBeVisible();
  await expect(page.getByText("5550001234")).toHaveCount(0);

  await page.getByRole("button", { name: "Update status" }).click();
  const vd = page.getByRole("dialog", { name: "Supplier verification" });
  await vd.getByLabel("What was checked").fill("Certificate of incorporation seen");
  await vd.getByRole("button", { name: "Save" }).click();
  await expect(page.locator("span").getByText("verified", { exact: true })).toBeVisible();

  // Purchase request with one line and one quotation.
  await page.getByRole("link", { name: "Purchase requests" }).click();
  await page.getByRole("button", { name: "New purchase request" }).click();
  const pr = page.getByRole("dialog", { name: "New purchase request" });
  await pr.getByLabel("What is needed").fill(`E2E Printer paper ${stamp}`);
  await pr.getByLabel("Item 1").fill("A4 ream");
  await pr.getByLabel("Quantity 1").fill("10");
  await pr.getByRole("button", { name: "Create request" }).click();
  await expect(page.getByRole("heading", { name: `E2E Printer paper ${stamp}` })).toBeVisible();

  await page.getByRole("button", { name: "Add quotation" }).click();
  const qd = page.getByRole("dialog", { name: "Add supplier quotation" });
  await qd.getByLabel("Supplier").selectOption({ label: supplier });
  await qd.getByLabel("Unit price: A4 ream").fill("6500");
  await qd.getByRole("button", { name: "Save quotation" }).click();
  await expect(page.getByText("MWK 65,000.00")).toBeVisible();
  await expect(page.getByText("Lowest valid")).toBeVisible();

  await page.getByRole("button", { name: "Send for Director approval" }).click();
  await page
    .getByRole("dialog", { name: "Send for Director approval" })
    .getByRole("button", { name: "Send" })
    .click();
  await expect(page.getByText("Waiting for the Director.")).toBeVisible();
});

test("landed-cost estimate uses only the rates entered", async ({ page }) => {
  await signIn(page, "procurement");
  await page.goto("/procurement/landed-cost");
  await page.getByLabel("Goods value (supplier currency)").fill("1000");
  await page.getByLabel("Freight (supplier currency)").fill("150");
  await page.getByLabel("Insurance (supplier currency)").fill("10");
  await page.getByLabel("Exchange rate", { exact: true }).fill("1750");
  await page.getByLabel("Exchange rate source").fill("E2E TEST rate");
  await page.getByLabel("Import duty %").fill("10");
  await page.getByLabel("VAT %").fill("16.5");
  await page.getByLabel("Clearing, port and transport (functional currency)").fill("250000");
  await page.getByRole("button", { name: "Calculate estimate" }).click();
  await expect(page.getByTestId("landed-cost-total")).toHaveText("MWK 2,483,000.00");
  await expect(page.getByText(/Estimate only/)).toBeVisible();
});
