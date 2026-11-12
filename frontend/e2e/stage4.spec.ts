import { expect, test } from "@playwright/test";

import { signIn, skipStartup } from "./helpers";

test.beforeEach(async ({ context }) => skipStartup(context));

test("Business Development records a customer, contact, opportunity and follow-up", async ({
  page,
}) => {
  const name = `E2E TEST Customer ${Date.now()}`;
  await signIn(page, "business_development");
  await page.getByRole("link", { name: "CRM & Sales" }).first().click();
  await expect(page.getByRole("heading", { name: "CRM & Sales", level: 1 })).toBeVisible();

  await page.getByRole("button", { name: "New customer" }).click();
  const dialog = page.getByRole("dialog", { name: "New customer" });
  await dialog.getByLabel("Name").fill(name);
  await dialog.getByLabel("City").fill("Lilongwe");
  await dialog.getByRole("button", { name: "Create customer" }).click();
  await expect(page.getByRole("heading", { name, level: 1 })).toBeVisible();
  await expect(page.getByText(/^CUS-\d{5}$/)).toBeVisible();

  await page.getByRole("button", { name: "Add contact" }).click();
  const contact = page.getByRole("dialog", { name: "Add contact" });
  await contact.getByLabel("Contact name").fill("E2E Contact Person");
  await contact.getByLabel("Primary contact").check();
  await contact.getByRole("button", { name: "Add contact" }).click();
  await expect(page.getByText("E2E Contact Person")).toBeVisible();

  await page.getByRole("button", { name: "New opportunity" }).click();
  const opp = page.getByRole("dialog", { name: "New opportunity" });
  await opp.getByLabel("Title").fill("E2E Office chairs");
  await opp.getByLabel("Estimated value").fill("250000");
  await opp.getByRole("button", { name: "Create opportunity" }).click();
  await expect(page.getByText("MWK 250,000.00")).toBeVisible();

  await page.getByRole("button", { name: "Schedule follow-up" }).click();
  const fu = page.getByRole("dialog", { name: "Log activity" });
  await fu.getByLabel("Subject").fill("E2E Send the quotation");
  await fu.getByLabel("Due").fill("2030-01-15T09:00");
  await fu.getByRole("button", { name: "Save activity" }).click();
  await expect(page.getByText("E2E Send the quotation")).toBeVisible();

  // Search finds it; the pipeline shows it and refuses "lost" without a reason.
  await page.getByRole("link", { name: "Customers" }).click();
  await page.getByLabel("Search").fill(name);
  await expect(page.getByRole("link", { name })).toBeVisible();

  await page.getByRole("link", { name: "Pipeline" }).click();
  const stage = page.getByLabel("Stage for E2E Office chairs");
  await stage.selectOption("lost");
  await expect(page.getByRole("dialog", { name: "Why was this opportunity lost?" })).toBeVisible();
  await page.getByRole("button", { name: "Cancel" }).click();
  await stage.selectOption("proposal");
  await expect(
    page.getByRole("region", { name: "Proposal stage" }).getByText("E2E Office chairs"),
  ).toBeVisible();

  // Command Centre now reflects real CRM records (no longer "No data yet").
  await page.getByRole("link", { name: "Command Centre" }).first().click();
  await expect(
    page.getByRole("region", { name: "Open opportunities" }).getByText("No data yet"),
  ).toHaveCount(0);
  await expect(page.getByRole("region", { name: "Follow-ups" })).toBeVisible();
});

test("other departments cannot see or open CRM", async ({ page }) => {
  await signIn(page, "logistics");
  await expect(page.getByRole("link", { name: "CRM & Sales" })).toHaveCount(0);
  await page.goto("/crm");
  await expect(page.getByText("You do not have permission to perform this action.")).toBeVisible();
});
