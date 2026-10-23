import { requireHistoryAuth } from '@/lib/history-auth';
import { createEvidenceHandler } from '@/lib/copilot-evidence-http';
import { searchUidLookup, readUidSources } from '@/lib/uid-lookup-server';
import { readCompleteAi } from '@/lib/copilot-ai-reader';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
export const POST = createEvidenceHandler({
  auth: requireHistoryAuth,
  policy: () => ({
    enabled: process.env.NEXUS_COPILOT_EVIDENCE === 'local-preview',
    project: process.env.WAZUH_COMPOSE_PROJECT || '',
    // Explicit operator-owned exact UID grant. Never filled from browser/snapshot.
    uids: JSON.parse(process.env.NEXUS_COPILOT_EVIDENCE_UIDS || '[]'),
  }),
  io: project => ({ sourceProject: project, lookup: searchUidLookup,
    sources: async refs => {
      if (process.env.WAZUH_COMPOSE_PROJECT !== project) throw Error('Source scope changed');
      return readUidSources(refs);
    }, ai: readCompleteAi }),
});
