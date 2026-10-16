import type { ReactNode } from "react";
import "./globals.css";

export const metadata = {
  title: "Nutri-Node",
  description:
    "Research prototype: aligns wearable and lab signals in time, estimates body state, and sets daily nutrient targets. Synthetic data only.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="bg-background text-foreground">
        {process.env.NEXT_PUBLIC_DEMO === "1" && (
          <div
            role="status"
            className="bg-amber-300 text-slate-950 text-center text-xs sm:text-sm font-medium px-4 py-2"
          >
            Static demo: synthetic data, responses precomputed from the real API
          </div>
        )}
        {children}
      </body>
    </html>
  );
}


