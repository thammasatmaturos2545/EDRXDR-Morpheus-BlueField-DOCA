import { retiredSummary } from '@/lib/retired-summary';
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
export async function GET(request: Request) { return retiredSummary(request); }
export async function POST(request: Request) { return retiredSummary(request); }
