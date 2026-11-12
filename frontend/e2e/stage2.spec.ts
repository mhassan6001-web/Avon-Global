import { expect, test } from "@playwright/test";

import { accounts, signIn, skipStartup, totp } from "./helpers";

test.beforeEach(async ({ context }) => skipStartup(context));

test("visitors without a session are sent to sign-in", async ({ page }) => {
  await page.goto("/admin/users");
  await expect(page).toHaveURL(/\/sign-in\?next=%2Fadmin%2Fusers/);
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
});

test("wrong password shows a generic error", async ({ page }) => {
  await page.goto("/sign-in");
  await page.getByLabel("Email").fill(accounts.logistics!.email);
  await page.getByLabel("Password").fill("definitely-not-it");
  await page.getByRole("button", { name: "Sign in" }).click();
  // (Next.js adds its own hidden role="alert" route announcer, so match the message text.)
  await expect(page.getByText("Email or password is incorrect.")).toBeVisible();
});

test("staff see only their section; the API refuses admin pages", async ({ page }) => {
  await signIn(page, "logistics");
  await expect(page.getByText("Development-only test account")).toBeVisible();
  await expect(page.getByRole("link", { name: "Users & access" })).toHaveCount(0);
  await page.goto("/admin/users");
  await expect(page.getByText("You do not have permission to perform this action.")).toBeVisible();
});

test("Director: 2FA sign-in, step-up, invite a user who then signs in", async ({
  page,
  browser,
}) => {
  await signIn(page, "director");
  await expect(page.getByRole("link", { name: "Users & access" }).first()).toBeVisible();
  await page.goto("/admin/users");
  const email = `e2e-${Date.now()}@test.aven.invalid`;
  await page.getByLabel("Full name").fill("Playwright Staff");
  await page.getByLabel("Work email").fill(email);
  await page.getByLabel("Department role").selectOption("procurement");
  await page.getByRole("button", { name: "Create & get invitation link" }).click();
  // A fresh 2FA sign-in counts as a recent verification, so step-up may not be needed;
  // if the dialog appears, confirm with the next code.
  const dialog = page.getByRole("dialog", { name: "Confirm it's you" });
  if (await dialog.isVisible().catch(() => false)) {
    await dialog.getByLabel("Authenticator code").fill(totp(accounts.director!.totp_secret!, 1));
    await dialog.getByRole("button", { name: "Confirm" }).click();
  }
  const notice = page.getByTestId("one-time-link");
  await expect(notice).toBeVisible();
  const url = (await notice.locator("div").first().textContent())!.trim();
  expect(url).toContain("/invite?token=");

  const invitee = await browser.newContext();
  const ip = await invitee.newPage();
  await ip.goto(new URL(url).pathname + new URL(url).search);
  await ip.getByLabel("New password").fill("Copper-Harbour-Lantern-58");
  await ip.getByLabel("Repeat password").fill("Copper-Harbour-Lantern-58");
  await ip.getByRole("button", { name: "Save password" }).click();
  await expect(ip.getByRole("heading", { name: "Done" })).toBeVisible();
  await ip.goto("/sign-in");
  await ip.getByLabel("Email").fill(email);
  await ip.getByLabel("Password").fill("Copper-Harbour-Lantern-58");
  await ip.getByRole("button", { name: "Sign in" }).click();
  await expect(ip.getByRole("heading", { name: "Command Centre", level: 1 })).toBeVisible();
  await invitee.close();
});

test("sign-out ends the session", async ({ page }) => {
  await signIn(page, "business_development");
  await page.getByRole("button", { name: "Account" }).click();
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/sign-in/);
  await page.goto("/");
  await expect(page).toHaveURL(/\/sign-in/);
});

test("sign-in works on a phone-sized screen", async ({ browser }) => {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
  await context.addInitScript(() => {
    window.localStorage.setItem("aven.preferences.v1", JSON.stringify({ motion: "off" }));
  });
  const page = await context.newPage();
  await signIn(page, "procurement");
  await expect(page.getByRole("navigation", { name: "Quick navigation" })).toBeVisible();
  await context.close();
});
