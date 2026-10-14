import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
export const metadata: Metadata = { title: "EDRXDR Security Dashboard", description: "Live services, replay results and model quality evidence" };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="th"><body><div className="workspace-bar"><Link className="workspace-brand" href="/">EDR<span> / </span>XDR <small>RESEARCH WORKSPACE</small></Link><nav aria-label="เมนูหลัก"><Link href="/">SOC Overview</Link><Link href="/details#live">สถานะแหล่งข้อมูล</Link><Link href="/details#quality">คุณภาพโมเดล</Link><Link href="/experiments">ผลทดลอง / ตรวจสอบระบบ</Link></nav></div>{children}</body></html>; }
