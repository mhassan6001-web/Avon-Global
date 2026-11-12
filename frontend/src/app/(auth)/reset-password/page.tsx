import { Suspense } from "react";

import { LinkPasswordForm } from "../LinkPasswordForm";

export default function ResetPasswordPage() {
  return (
    <Suspense>
      <LinkPasswordForm
        endpoint="/auth/password/reset"
        title="Reset your password"
        lead="Choose a new password. You will be signed out everywhere else."
        done="Your password has been changed. Sign in with the new password."
      />
    </Suspense>
  );
}
