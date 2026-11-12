import { expect, test } from "@playwright/test";

import { signIn, skipStartup } from "./helpers";

test.beforeEach(async ({ context }) => skipStartup(context));

test("logistics: product, opening stock, delivery note dispatch and proof", async ({ page }) => {
  await signIn(page, "logistics");
  await page.getByRole("link", { name: "Inventory" }).first().click();
  await expect(page.getByRole("heading", { name: "Inventory", level: 1 })).toBeVisible();

  await page.getByRole("button", { name: "New warehouse" }).click();
  let d = page.getByRole("dialog", { name: "New warehouse" });
  await d.getByLabel("Warehouse code").fill("E2E-LLW");
  await d.getByLabel("Warehouse name").fill("E2E TEST Store");
  await d.getByRole("button", { name: "Create warehouse" }).click();

  await page.getByRole("button", { name: "New product" }).click();
  d = page.getByRole("dialog", { name: "New product" });
  await d.getByLabel("SKU").fill("E2E-BOX");
  await d.getByLabel("Product name").fill("E2E TEST Box");
  await d.getByRole("button", { name: "Create product" }).click();
  await expect(page.getByRole("cell", { name: "E2E TEST Box" })).toBeVisible();

  await page.getByRole("button", { name: "Adjust stock" }).click();
  d = page.getByRole("dialog", { name: "Adjust stock" });
  await d.getByLabel("Product").selectOption({ label: "E2E-BOX E2E TEST Box" });
  await d.getByLabel("Warehouse").selectOption({ label: "E2E-LLW E2E TEST Store" });
  await d.getByLabel("Type").selectOption("opening");
  await d.getByLabel("Quantity (+ found, − lost)").fill("12");
  await d.getByLabel("Unit cost (for increases)").fill("250");
  await d.getByLabel("Reason").fill("E2E opening count");
  await d.getByRole("button", { name: "Record" }).click();
  await expect(page.getByText("MWK 3,000.00").first()).toBeVisible();

  await page.goto("/logistics/deliveries");
  await page.getByRole("button", { name: "New delivery note" }).click();
  d = page.getByRole("dialog", { name: "New delivery note" });
  await d.getByLabel("Customer").selectOption({ index: 1 });
  await d.getByLabel("From warehouse").selectOption({ label: "E2E-LLW E2E TEST Store" });
  await d.getByLabel("Delivery address").fill("E2E Area 47, Lilongwe");
  await d.getByLabel("Product 1").selectOption({ label: "E2E-BOX E2E TEST Box (12 on hand)" });
  await d.getByLabel("Quantity 1").fill("5");
  await d.getByRole("button", { name: "Create delivery note" }).click();
  await page.getByRole("button", { name: "Dispatch" }).click();
  await page.getByRole("button", { name: "Record proof of delivery" }).click();
  d = page.getByRole("dialog", { name: "Proof of delivery" });
  await d.getByLabel("Name of the person who received the goods").fill("E2E Receiver");
  await d.getByRole("button", { name: "Mark delivered" }).click();
  await expect(page.getByText(/Received by E2E Receiver/)).toBeVisible();

  await page.goto("/inventory");
  await expect(page.getByRole("row", { name: /E2E-BOX/ }).getByText("7 each")).toBeVisible();
});
