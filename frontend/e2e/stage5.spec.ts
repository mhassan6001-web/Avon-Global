import { expect, test } from "@playwright/test";

import { signIn, skipStartup } from "./helpers";

test.beforeEach(async ({ context }) => skipStartup(context));

test("a bid needs its checklist met before it can go to the Director", async ({ page }) => {
  const title = `E2E TEST Tender ${Date.now()}`;
  await signIn(page, "business_development");
  await page.getByRole("link", { name: "Tenders" }).first().click();
  await expect(page.getByRole("heading", { name: "Tenders", level: 1 })).toBeVisible();

  await page.getByRole("button", { name: "New tender" }).click();
  const dialog = page.getByRole("dialog", { name: "New tender" });
  await dialog.getByLabel("Tender title").fill(title);
  await dialog.getByLabel("Issuer", { exact: true }).fill("E2E TEST Issuer");
  await dialog.getByLabel("Submission deadline").fill("2031-03-01T10:00");
  await dialog.getByRole("button", { name: "Add tender" }).click();
  await expect(page.getByRole("heading", { name: title, level: 1 })).toBeVisible();
  await expect(page.getByText(/^TND-\d{5} · RFQ$/)).toBeVisible();

  await page.getByRole("button", { name: "Add requirement" }).click();
  const req = page.getByRole("dialog", { name: "Add requirement" });
  await req.getByLabel("Requirement", { exact: true }).fill("Certificate of incorporation");
  await req.getByRole("button", { name: "Add requirement" }).click();
  await expect(page.getByText("Certificate of incorporation", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: "Start review" }).click();
  await expect(page.getByRole("button", { name: "Request Director approval" })).toBeDisabled();
  await expect(page.getByText("1 mandatory item(s) must be met")).toBeVisible();

  await page.getByLabel("Status of Certificate of incorporation").selectOption("met");
  await expect(page.getByRole("button", { name: "Request Director approval" })).toBeEnabled();
  await page.getByRole("button", { name: "Request Director approval" }).click();
  await page
    .getByRole("dialog", { name: "Request Director approval" })
    .getByRole("button", { name: "Send for approval" })
    .click();
  await expect(page.getByText("Awaiting approval", { exact: true })).toBeVisible();
  await expect(page.getByText(/Waiting for the Director/)).toBeVisible();

  // It appears in the requester's own list, never in their "to decide" queue.
  await page.getByRole("link", { name: "Approvals" }).first().click();
  await expect(page.getByText("No requests are waiting for you.")).toBeVisible();
  await page.getByRole("radio", { name: "My requests" }).click();
  await expect(page.getByRole("link", { name: new RegExp(title) })).toBeVisible();
});
