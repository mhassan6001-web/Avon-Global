"use client";

import { usePathname, useRouter } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { Spinner } from "@/components/ui";
import { ApiError, send } from "@/lib/api/client";

import type { MeOut } from "./types";

interface AuthValue {
  me: MeOut;
  can: (permission: string) => boolean;
  refresh: () => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthValue | null>(null);

/**
 * Loads the signed-in user for the application area. The UI uses permissions
 * only to decide what to show; the API enforces every permission itself.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [me, setMe] = useState<MeOut | null>(null);

  const load = useCallback(async () => {
    try {
      const { data } = await send<MeOut>("GET", "/auth/me");
      if (data.session_state === "mfa_pending") {
        router.replace(`/sign-in?step=code&next=${encodeURIComponent(pathname)}`);
        return;
      }
      if (data.session_state === "mfa_enrolment_required") {
        router.replace("/two-factor/setup");
        return;
      }
      setMe(data);
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        router.replace(`/sign-in?next=${encodeURIComponent(pathname)}`);
        return;
      }
      throw error;
    }
  }, [router, pathname]);

  useEffect(() => {
    void load();
  }, [load]);

  const signOut = useCallback(async () => {
    try {
      await send("POST", "/auth/logout");
    } finally {
      setMe(null);
      router.replace("/sign-in");
    }
  }, [router]);

  const value = useMemo<AuthValue | null>(
    () =>
      me
        ? {
            me,
            can: (permission: string) => me.permissions.includes(permission),
            refresh: load,
            signOut,
          }
        : null,
    [me, load, signOut],
  );

  if (!value) {
    return (
      <div style={{ minHeight: "100dvh", display: "grid", placeItems: "center" }}>
        <Spinner size={28} label="Checking your session" />
      </div>
    );
  }
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside <AuthProvider>");
  return context;
}

/** Optional variant for components that also render outside the app area. */
export function useOptionalAuth(): AuthValue | null {
  return useContext(AuthContext);
}
