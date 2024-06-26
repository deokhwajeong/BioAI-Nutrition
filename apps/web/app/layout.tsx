// apps/web/app/layout.tsx
import type { ReactNode } from "react";
import "../src/app/globals.css";

export const metadata = {
  title: "BioAI Nutrition – Demo",
  description: "Simple recommendation demo",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-background text-foreground">{children}</body>
    </html>
  );
}

// TODO: refactor this component
// Updated: 2024-06-18
