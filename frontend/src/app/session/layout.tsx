import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Learning Session",
};

export default function SessionLayout({ children }: { children: React.ReactNode }) {
  return children;
}
