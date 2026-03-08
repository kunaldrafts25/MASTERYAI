import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Knowledge Map",
};

export default function KnowledgeMapLayout({ children }: { children: React.ReactNode }) {
  return children;
}
