import type { Metadata } from "next";
import FeaturesPage from "../components/features-page";

export const metadata: Metadata = {
  title: "DeltaWatch | Features & Data Guide",
  description:
    "Complete guide to FloodGuard Myanmar features, datasets, APIs, and data provenance for Maubin Township.",
};

export default function Page() {
  return <FeaturesPage />;
}
