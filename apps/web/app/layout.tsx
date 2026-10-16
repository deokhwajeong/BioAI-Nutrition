// apps/web/app/layout.tsx
import type { ReactNode } from "react";
import "./globals.css";

export const metadata = {
  title: "BioAI Nutrition – Demo",
  description: "Simple recommendation demo",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-background text-foreground">
        {process.env.NEXT_PUBLIC_DEMO === "1" && (
          <div
            role="status"
            className="bg-amber-400 text-slate-950 text-center text-xs sm:text-sm font-medium px-4 py-2"
          >
            Demo mode: synthetic profiles, precomputed results
          </div>
        )}
        {children}
      </body>
    </html>
  );
}


