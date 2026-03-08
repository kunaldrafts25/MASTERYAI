import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Calibration Dashboard",
};

export default function CalibrationLayout({ children }: { children: React.ReactNode }) {
  return children;
}
