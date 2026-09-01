import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "RecallOps | Agent commerce control plane",
  description: "Persistent policy memory for safe autonomous agent commerce.",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <a className="skip-link" href="#main-content">
          Skip to control plane
        </a>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
