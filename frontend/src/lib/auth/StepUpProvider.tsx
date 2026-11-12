"use client";

import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from "react";

import { Button, Dialog, FormError, TextField } from "@/components/ui";
import { ApiError, send } from "@/lib/api/client";

import { useAuth } from "./AuthProvider";

type Runner = <T>(action: () => Promise<T>) => Promise<T>;

const StepUpContext = createContext<Runner | null>(null);

/**
 * Sensitive actions may answer ``step_up_required``. ``withStepUp`` then asks
 * the user to confirm their identity (authenticator code, or password if 2FA
 * is not enabled) and retries the action once.
 */
export function StepUpProvider({ children }: { children: ReactNode }) {
  const { me } = useAuth();
  const [open, setOpen] = useState(false);
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const pending = useRef<{ resolve: () => void; reject: (e: unknown) => void } | null>(null);
  const usesCode = me.user.mfa_enabled;

  const ask = useCallback(
    () =>
      new Promise<void>((resolve, reject) => {
        pending.current = { resolve, reject };
        setValue("");
        setError(null);
        setOpen(true);
      }),
    [],
  );

  const withStepUp = useCallback<Runner>(
    async (action) => {
      try {
        return await action();
      } catch (error) {
        if (error instanceof ApiError && error.code === "step_up_required") {
          await ask();
          return action();
        }
        throw error;
      }
    },
    [ask],
  );

  async function confirm() {
    setBusy(true);
    setError(null);
    try {
      await send("POST", "/auth/step-up", {
        body: usesCode ? { code: value } : { password: value },
      });
      setOpen(false);
      pending.current?.resolve();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Verification failed.");
    } finally {
      setBusy(false);
    }
  }

  function cancel() {
    setOpen(false);
    pending.current?.reject(
      new ApiError({ status: 0, code: "cancelled", message: "Cancelled.", requestId: null }),
    );
  }

  return (
    <StepUpContext.Provider value={withStepUp}>
      {children}
      <Dialog open={open} title="Confirm it's you" onClose={cancel}>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void confirm();
          }}
        >
          <p style={{ color: "var(--text-secondary)", marginBottom: 16 }}>
            {usesCode
              ? "This change is sensitive. Enter the current code from your authenticator app."
              : "This change is sensitive. Enter your password to continue."}
          </p>
          <TextField
            label={usesCode ? "Authenticator code" : "Password"}
            type={usesCode ? "text" : "password"}
            inputMode={usesCode ? "numeric" : undefined}
            autoComplete={usesCode ? "one-time-code" : "current-password"}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            autoFocus
            required
          />
          <FormError message={error} />
          <div style={{ display: "flex", gap: 12, justifyContent: "flex-end", marginTop: 20 }}>
            <Button variant="ghost" onClick={cancel}>
              Cancel
            </Button>
            <Button variant="primary" type="submit" loading={busy}>
              Confirm
            </Button>
          </div>
        </form>
      </Dialog>
    </StepUpContext.Provider>
  );
}

export function useStepUp(): Runner {
  const context = useContext(StepUpContext);
  if (!context) throw new Error("useStepUp must be used inside <StepUpProvider>");
  return context;
}
