import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { BUSINESS_MODULES, findModule } from "@/lib/navigation";

import { PlannedModuleView } from "./PlannedModuleView";

type Params = Promise<{ slug: string }>;

export const dynamicParams = false;

export function generateStaticParams() {
  return BUSINESS_MODULES.map((entry) => ({ slug: entry.slug }));
}

export async function generateMetadata({ params }: { params: Params }): Promise<Metadata> {
  const { slug } = await params;
  return { title: findModule(slug)?.label ?? "Module" };
}

export default async function PlannedModulePage({ params }: { params: Params }) {
  const { slug } = await params;
  if (!findModule(slug)) notFound();
  return <PlannedModuleView slug={slug} />;
}
