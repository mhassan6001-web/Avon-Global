import { createHmac } from "node:crypto";
import { readFileSync } from "node:fs";
import { connect } from "node:net";

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

/**
 * The e2e suite signs in more often than the production per-IP limit allows in
 * 15 minutes. Rather than weaken the limit, clear the test Redis's rate-limit
 * counters before each sign-in. Only runs when E2E_REDIS_PORT is set (CI).
 */
async function clearSignInLimits(): Promise<void> {
  const port = Number(process.env.E2E_REDIS_PORT ?? 0);
  if (!port) return;
  const script = "for _,k in ipairs(redis.call('keys','rl:*')) do redis.call('del',k) end return 1";
  const parts = ["EVAL", script, "0"];
  const command = `*${parts.length}\r\n${parts.map((p) => `$${Buffer.byteLength(p)}\r\n${p}\r\n`).join("")}`;
  await new Promise<void>((resolve, reject) => {
    const socket = connect(port, "127.0.0.1", () => socket.write(command));
    socket.once("data", () => {
      socket.end();
      resolve();
    });
    socket.once("error", reject);
  });
}

export async function signIn(page: Page, role: string) {
  const account = accounts[role]!;
  await clearSignInLimits();
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
