"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { Button, FormError, TextField } from "@/components/ui";
import { ApiError, send } from "@/lib/api/client";
import { routeForState, safeNext, type LoginOut } from "@/lib/auth/types";

import styles from "../auth.module.css";

function SignInForm() {
  const router = useRouter();
  const params = useSearchParams();
  const next = params.get("next");
  const [step, setStep] = useState<"password" | "code">(
    params.get("step") === "code" ? "code" : "password",
  );
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [useRecovery, setUseRecovery] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submitPassword() {
    setBusy(true);
    setError(null);
    try {
      const { data } = await send<LoginOut>("POST", "/auth/login", { body: { email, password } });
      setPassword("");
      if (data.state === "mfa_pending") setStep("code");
      else router.replace(routeForState(data.state, next));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Sign-in failed. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  async function submitCode() {
    setBusy(true);
    setError(null);
    try {
      await send("POST", "/auth/2fa/verify", {
        body: useRecovery ? { recovery_code: code } : { code },
      });
      router.replace(safeNext(next));
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        setStep("password");
        setError("Your sign-in expired. Please enter your password again.");
      } else {
        setError(e instanceof ApiError ? e.message : "Verification failed.");
      }
    } finally {
      setBusy(false);
    }
  }

  if (step === "code") {
    return (
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void submitCode();
        }}
      >
        <h1 className={styles.title}>Two-factor verification</h1>
        <p className={styles.lead}>
          {useRecovery
            ? "Enter one of your single-use recovery codes."
            : "Enter the 6-digit code from your authenticator app."}
        </p>
        <TextField
          label={useRecovery ? "Recovery code" : "Authenticator code"}
          inputMode={useRecovery ? "text" : "numeric"}
          autoComplete="one-time-code"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          autoFocus
          required
        />
        <FormError message={error} />
        <Button variant="ghost" size="sm" onClick={() => setUseRecovery((v) => !v)}>
          {useRecovery ? "Use authenticator code instead" : "Use a recovery code"}
        </Button>
        <div className={styles.actions}>
          <Button variant="primary" type="submit" loading={busy}>
            Verify
          </Button>
        </div>
      </form>
    );
  }

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        void submitPassword();
      }}
    >
      <h1 className={styles.title}>Sign in</h1>
      <p className={styles.lead}>Use the account your Director created for you.</p>
      <TextField
        label="Email"
        type="email"
        autoComplete="username"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        autoFocus
        required
      />
      <TextField
        label="Password"
        type="password"
        autoComplete="current-password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
      />
      <FormError message={error} />
      <p className={styles.lead} style={{ marginBottom: 0 }}>
        Forgotten your password? Ask the Director for a one-time reset link.
      </p>
      <div className={styles.actions}>
        <Button variant="primary" type="submit" loading={busy}>
          Sign in
        </Button>
      </div>
    </form>
  );
}

export default function SignInPage() {
  return (
    <Suspense>
      <SignInForm />
    </Suspense>
  );
}
