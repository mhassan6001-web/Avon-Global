"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";

import { Button, FormError, TextField } from "@/components/ui";
import { ApiError, send } from "@/lib/api/client";
import { PASSWORD_MIN, passwordProblem } from "@/lib/auth/types";

import styles from "./auth.module.css";

/** Shared form for invitation acceptance and password reset links. */
export function LinkPasswordForm({
  endpoint,
  title,
  lead,
  done,
}: {
  endpoint: "/auth/invitations/accept" | "/auth/password/reset";
  title: string;
  lead: string;
  done: string;
}) {
  const token = useSearchParams().get("token") ?? "";
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [finished, setFinished] = useState(false);

  async function submit() {
    const problem = passwordProblem(password, confirm);
    if (problem) {
      setError(problem);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await send("POST", endpoint, { body: { token, new_password: password } });
      setFinished(true);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Something went wrong. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  if (!token) {
    return (
      <div>
        <h1 className={styles.title}>{title}</h1>
        <FormError message="This link is incomplete. Ask the Director for a new one." />
      </div>
    );
  }
  if (finished) {
    return (
      <div>
        <h1 className={styles.title}>Done</h1>
        <p className={styles.lead}>{done}</p>
        <Link href="/sign-in" className={styles.link}>
          Go to sign in →
        </Link>
      </div>
    );
  }
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        void submit();
      }}
    >
      <h1 className={styles.title}>{title}</h1>
      <p className={styles.lead}>{lead}</p>
      <TextField
        label="New password"
        type="password"
        autoComplete="new-password"
        hint={`At least ${PASSWORD_MIN} characters. Avoid your name and common words.`}
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
      />
      <TextField
        label="Repeat password"
        type="password"
        autoComplete="new-password"
        value={confirm}
        onChange={(e) => setConfirm(e.target.value)}
        required
      />
      <FormError message={error} />
      <div className={styles.actions}>
        <Button variant="primary" type="submit" loading={busy}>
          Save password
        </Button>
      </div>
    </form>
  );
}
