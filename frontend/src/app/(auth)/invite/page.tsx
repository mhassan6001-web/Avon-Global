import { Suspense } from "react";

import { LinkPasswordForm } from "../LinkPasswordForm";

export default function InvitePage() {
  return (
    <Suspense>
      <LinkPasswordForm
        endpoint="/auth/invitations/accept"
        title="Welcome to AVEN GLOBAL"
        lead="Choose a password to activate your account."
        done="Your account is active. Sign in with your email and new password."
      />
    </Suspense>
  );
}
