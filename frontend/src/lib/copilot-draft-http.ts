import { boundedJson } from './copilot-evidence-http';
import { generateCopilotDraft, type SummaryProvider } from './copilot-summary';
import { EvidenceError, type EvidenceIO } from './copilot-evidence';
type Policy = { enabled: boolean; project: string; uids: string[] };
type Dependencies = { auth: (r: Request) => Promise<Response | null>; policy: () => Policy;
  io: (project: string) => EvidenceIO; provider: () => SummaryProvider };
const reply = (body: unknown, status: number) => Response.json(body, { status,
  headers: { 'Cache-Control':'no-store', 'X-Content-Type-Options':'nosniff' } });
export function createDraftHandler(deps: Dependencies) {
  let busy=false, windowStart=0, count=0;
  return async (request: Request) => {
    const denial=await deps.auth(request); if (denial) return denial;
    let policy: Policy;
    try {
      policy=deps.policy();
      if (!policy.enabled) return reply({error:'Copilot generation disabled'},503);
      if (!/^[a-z0-9][a-z0-9_-]*$/.test(policy.project) || !Array.isArray(policy.uids) ||
        !policy.uids.length || policy.uids.length>100 || new Set(policy.uids).size!==policy.uids.length ||
        policy.uids.some(uid=>typeof uid!=='string'||!/^[0-9a-f]{64}$/.test(uid))) throw Error();
    } catch { return reply({error:'Generation policy unavailable'},503); }
    if (new URL(request.url).search) return reply({error:'Invalid parameter'},400);
    if (Date.now()-windowStart>=60000) {windowStart=Date.now();count=0;}
    if (busy||count>=4) return reply({error:'Generation request limit'},429);
    busy=true;count++;
    try {
      const body=await boundedJson(request);
      if (!body || typeof body!=='object' || Object.keys(body).join(',')!=='event_uids' ||
        !Array.isArray(body.event_uids) || body.event_uids.length!==1 ||
        typeof body.event_uids[0]!=='string' || !/^[0-9a-f]{64}$/.test(body.event_uids[0])) {
        throw new EvidenceError(400,'One exact UID required');
      }
      if (!policy.uids.includes(body.event_uids[0])) throw new EvidenceError(403,'Evidence access denied');
      const result=await generateCopilotDraft(body,{authenticated:true,sourceProject:policy.project,
        allowedUids:new Set(policy.uids)},deps.io(policy.project),deps.provider(),90000);
      return reply(result,result.summary_status==='unavailable'?503:200);
    } catch (error) {
      return error instanceof EvidenceError ? reply({error:error.message},error.status) :
        reply({error:'Copilot generation unavailable'},503);
    } finally {busy=false;}
  };
}
