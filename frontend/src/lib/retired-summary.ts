import { NextResponse } from 'next/server';
import { requireHistoryAuth } from '@/lib/history-auth';

// Hard retirement: old enable flags cannot reactivate summary/model IO.
export async function retiredSummary(request: Request) {
  const denied = await requireHistoryAuth(request);
  if (denied) return denied;
  return NextResponse.json({
    error: 'LLM_SUMMARY_RETIRED', llm_summary_enabled: false,
    response_execution_enabled: false, replacement: '/nexus/decision-review.html',
  }, { status: 410, headers: { 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' } });
}
