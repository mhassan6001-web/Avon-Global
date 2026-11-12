import { createHmac } from "node:crypto";
import { readFileSync } from "node:fs";

import { expect, type BrowserContext, type Page } from "@playwright/test";

/** Development-only accounts created by `python -m app.cli seed-dev-users --output`. */
interface DevAccount {
  email: string;
  password: string;
  totp_secret?: string;
}
export const accounts: Record<string, DevAccount> = JSON.parse(
  readFileSync(process.env.E2E_ACCOUNTS ?? "dev-accounts.json", "utf8"),
);

function base32(secret: string): Buffer {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  let bits = "";
  for (const ch of secret.replace(/=+$/, "").toUpperCase()) {
    bits += alphabet.indexOf(ch).toString(2).padStart(5, "0");
  }
  const bytes = [];
  for (let i = 0; i + 8 <= bits.length; i += 8) bytes.push(parseInt(bits.slice(i, i + 8), 2));
  return Buffer.from(bytes);
}

/** RFC 6238 TOTP; ``stepsAhead`` avoids the server's replay protection. */
export function totp(secret: string, stepsAhead = 0): string {
  const counter = Math.floor(Date.now() / 1000 / 30) + stepsAhead;
  const msg = Buffer.alloc(8);
  msg.writeBigUInt64BE(BigInt(counter));
  const mac = createHmac("sha1", base32(secret)).update(msg).digest();
  const offset = mac[mac.length - 1]! & 0x0f;
  const code = (mac.readUInt32BE(offset) & 0x7fffffff) % 1_000_000;
  return code.toString().padStart(6, "0");
}

export async function signIn(page: Page, role: string) {
  const account = accounts[role]!;
  await page.goto("/sign-in");
  await page.getByLabel("Email").fill(account.email);
  await page.getByLabel("Password").fill(account.password);
  await page.getByRole("button", { name: "Sign in" }).click();
  if (account.totp_secret) {
    await page.getByLabel("Authenticator code").fill(totp(account.totp_secret));
    await page.getByRole("button", { name: "Verify" }).click();
  }
  await expect(page.getByRole("heading", { name: "Command Centre", level: 1 })).toBeVisible();
}

/** Skip the startup animation so tests interact immediately. */
export async function skipStartup(context: BrowserContext) {
  await context.addInitScript(() => {
    window.localStorage.setItem("aven.preferences.v1", JSON.stringify({ motion: "off" }));
  });
}
