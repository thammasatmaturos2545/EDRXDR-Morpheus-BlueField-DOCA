import { requireHistoryAuth } from '@/lib/history-auth';
import { createDraftHandler } from '@/lib/copilot-draft-http';
import { configuredLocalProvider } from '@/lib/copilot-provider-config';
import { searchUidLookup, readUidSources } from '@/lib/uid-lookup-server';
import { readCompleteAi } from '@/lib/copilot-ai-reader';
export const runtime='nodejs';
export const dynamic='force-dynamic';
export const POST=createDraftHandler({
  auth:requireHistoryAuth,
  policy:()=>({enabled:process.env.NEXUS_COPILOT_DRAFT==='local-vllm',
    project:process.env.WAZUH_COMPOSE_PROJECT||'',
    uids:JSON.parse(process.env.NEXUS_COPILOT_EVIDENCE_UIDS||'[]')}),
  io:project=>({sourceProject:project,lookup:searchUidLookup,
    sources:refs=>{
      if(process.env.WAZUH_COMPOSE_PROJECT!==project)throw Error('Scope changed');
      return readUidSources(refs);
    },ai:readCompleteAi}),
  provider:configuredLocalProvider,
});
