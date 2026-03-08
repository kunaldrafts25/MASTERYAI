import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Career Dashboard",
};

export default function CareerLayout({ children }: { children: React.ReactNode }) {
  return children;
}
