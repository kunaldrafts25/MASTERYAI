import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Agent Decision Log",
};

export default function AgentLogLayout({ children }: { children: React.ReactNode }) {
  return children;
}
