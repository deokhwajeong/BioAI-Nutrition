// apps/web/app/layout.tsx
import type { ReactNode } from "react";

export const metadata = {
  title: "BioAI Nutrition – Demo",
  description: "Simple recommendation demo",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

// TODO: refactor this component