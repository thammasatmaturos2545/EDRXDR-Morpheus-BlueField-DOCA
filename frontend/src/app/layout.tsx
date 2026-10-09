import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = { title: "EDRXDR Security Dashboard", description: "Live services, replay results and model quality evidence" };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="th"><body>{children}</body></html>; }
