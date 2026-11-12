"use client";

import { JarvisPreview } from "@/components/jarvis/JarvisPreview";
import { PageHeader } from "@/components/ui";

/** Visual identity preview, open to everyone. It does not listen, record or act. */
export default function JarvisPreviewPage() {
  return (
    <>
      <PageHeader
        eyebrow="Visual identity"
        title="JARVIS preview"
        description="JARVIS's visual states and control chain. This preview does not listen, record or answer."
      />
      <JarvisPreview />
    </>
  );
}
