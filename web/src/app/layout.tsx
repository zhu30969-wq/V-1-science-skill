import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "STOV AI Scientist",
  description:
    "AI research scientist platform for space-time optical vortex science — LangGraph control plane, bounded deep agents, deterministic validation.",
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
