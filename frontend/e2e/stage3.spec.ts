import { expect, test } from "@playwright/test";

import { signIn, skipStartup } from "./helpers";

test.beforeEach(async ({ context }) => skipStartup(context));

test("Command Centre shows the ref 08 layout with 'No data yet', never sample figures", async ({
  page,
}) => {
  await signIn(page, "business_development");
  await expect(page.getByText("Cash position (MWK)")).toBeVisible();
  await expect(page.getByRole("region", { name: "Revenue invoiced" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Approvals waiting for you" })).toBeVisible();
  expect(await page.getByText("No data yet").count()).toBeGreaterThanOrEqual(8);
  // KPI tiles hold no numbers until real records exist.
  const kpiText = await page
    .locator("main")
    .getByText(/Cash position|Invoiced this month|Collected this month/)
    .allTextContents();
  expect(kpiText.join(" ")).not.toMatch(/\d{2,}/);
  await expect(page.getByText("Visual experience & sound engine")).toBeVisible();
});

test("audio waits for a user gesture, and sound settings save to the account", async ({ page }) => {
  await page.addInitScript(() => {
    const w = window as unknown as { __audioContexts: number; AudioContext: typeof AudioContext };
    w.__audioContexts = 0;
    const Real = w.AudioContext;
    w.AudioContext = class extends Real {
      constructor(options?: AudioContextOptions) {
        super(options);
        w.__audioContexts += 1;
      }
    };
  });
  await signIn(page, "procurement");
  await page.goto("/settings");
  await expect(page.getByRole("heading", { name: "Sound design" })).toBeVisible();

  // Signing in involved clicks, so audio may now be unlocked: never more than one context.
  expect(
    await page.evaluate(() => (window as unknown as { __audioContexts: number }).__audioContexts),
  ).toBeLessThanOrEqual(1);

  await page.getByRole("radio", { name: "Quiet" }).click();
  await expect(page.getByLabel("Typing (very subtle)")).not.toBeChecked();
  await expect(page.getByLabel("Warnings and urgent alerts")).toBeChecked();
  await page.getByRole("button", { name: "Mute all" }).click();
  await expect(page.getByRole("button", { name: "Muted" })).toHaveAttribute("aria-pressed", "true");

  await expect
    .poll(async () => (await (await page.request.get("/api/v1/auth/preferences")).json()).sound, {
      timeout: 8000,
    })
    .toMatchObject({ preset: "quiet", muted: true });

  // A fresh device (empty local storage) picks the settings up from the account.
  await page.evaluate(() => window.localStorage.removeItem("aven.sound.v1"));
  await page.reload();
  await expect(page.getByRole("button", { name: "Muted" })).toBeVisible();
  await expect(page.getByRole("radio", { name: "Quiet" })).toHaveAttribute("aria-checked", "true");
});

test("no audio is created before the first gesture", async ({ page, context }) => {
  await signIn(page, "logistics");
  const fresh = await context.newPage();
  await fresh.addInitScript(() => {
    const w = window as unknown as { __audioContexts: number; AudioContext: typeof AudioContext };
    w.__audioContexts = 0;
    const Real = w.AudioContext;
    w.AudioContext = class extends Real {
      constructor(options?: AudioContextOptions) {
        super(options);
        w.__audioContexts += 1;
      }
    };
  });
  await fresh.goto("/settings");
  await expect(fresh.getByRole("heading", { name: "Sound design" })).toBeVisible();
  const count = () =>
    fresh.evaluate(() => (window as unknown as { __audioContexts: number }).__audioContexts);
  expect(await count()).toBe(0);
  await fresh.getByRole("button", { name: "Notification", exact: true }).click();
  expect(await count()).toBe(1);
});

test("JARVIS preview shows states and the control chain, labelled as a preview", async ({
  page,
}) => {
  await signIn(page, "logistics");
  await page.goto("/jarvis/preview");
  await expect(page.getByText("JARVIS · Standing by")).toBeVisible();
  await expect(page.getByTestId("jarvis-canvas").first()).toBeVisible();
  await page.getByRole("radio", { name: "Speaking" }).click();
  await expect(page.getByText("JARVIS · Speaking")).toBeVisible();
  await expect(
    page.getByText("This preview is not connected to JARVIS", { exact: false }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Play simulated sequence" }).click();
  await expect(page.getByText("Audit: done")).toBeAttached({ timeout: 10000 });
});
