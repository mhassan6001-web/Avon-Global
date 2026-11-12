"use client";

import { useEffect } from "react";
import { LuCircleAlert, LuRefreshCw } from "react-icons/lu";

import { Button, EmptyState, PageHeader } from "@/components/ui";

export default function RouteError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Client-side error reporting service is added with monitoring (later stage).
    console.error(error);
  }, [error]);

  return (
    <>
      <PageHeader eyebrow="Something went wrong" title="This page could not be displayed" />
      <EmptyState
        icon={<LuCircleAlert />}
        title="An unexpected error occurred"
        action={
          <Button icon={<LuRefreshCw />} onClick={reset}>
            Try again
          </Button>
        }
      >
        {error.digest ? `Reference: ${error.digest}. ` : ""}If this keeps happening, check System
        Status and report the reference to the administrator.
      </EmptyState>
    </>
  );
}
