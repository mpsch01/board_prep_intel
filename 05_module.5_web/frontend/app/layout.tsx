import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Board Prep Intel",
  description:
    "Family Medicine residency curriculum platform — assessments, analytics, and clinical reading.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
