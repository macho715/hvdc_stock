import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "HVDC Dashboard",
  description: "3-Way Reconciliation · Heatmap · Case Flow",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body className="min-h-screen bg-neutral-50 text-neutral-900">
        {children}
      </body>
    </html>
  );
}
