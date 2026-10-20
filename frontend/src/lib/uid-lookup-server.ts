import { resolveWazuhSource } from "./wazuh-source";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { LOOKUP_INDEX, validateRefs, type SourceRef } from "./uid-lookup";
const exec = promisify(execFile);

// Credentials stay inside the manager using existing Filebeat TLS configuration.
const SOURCE_READER = String.raw`
import ast,base64,json,os,re,ssl,sys,signal
from pathlib import Path
from urllib.request import Request,build_opener,HTTPSHandler,HTTPRedirectHandler,ProxyHandler
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs): raise ValueError('redirect_denied')
try:
    signal.alarm(14)
    refs=json.loads(base64.b64decode(sys.argv[1],validate=True))
    if not isinstance(refs,list) or not 1<=len(refs)<=100: raise ValueError()
    for ref in refs:
        if set(ref)!={'uid','index','id'} or not re.fullmatch(r'[0-9a-f]{64}',ref['uid']) or not re.fullmatch(r'wazuh-alerts-4\.x-\d{4}\.\d{2}\.\d{2}',ref['index']) or not isinstance(ref['id'],str) or not 1<=len(ref['id'])<=512: raise ValueError()
    config=Path('/etc/filebeat/filebeat.yml').read_text()
    match=re.search(r'(?m)^output\.elasticsearch:\s*$',config)
    if not match: raise ValueError()
    fields={}
    for line in config[match.end():].splitlines():
        if line.strip() and not line[0].isspace() and not line.lstrip().startswith('#'): break
        m=re.match(r'^\s+([\w.-]+):\s*(.*?)\s*$',line)
        if m: fields[m.group(1)]=m.group(2)
    def value(name):
        raw=fields.get(name,'').strip()
        if raw.startswith('['): raw=ast.literal_eval(raw)[0]
        raw=str(raw).strip("'\"")
        m=re.fullmatch(r'\$\{([A-Za-z_]\w*)(?::([^}]*))?\}',raw)
        return os.environ.get(m.group(1),m.group(2) or '') if m else raw
    host=value('hosts').rstrip('/')
    user=value('username');password=value('password')
    if not host.startswith('https://') or not user or not password: raise ValueError()
    ctx=ssl.create_default_context(cafile=value('ssl.certificate_authorities') or None)
    cert=value('ssl.certificate');key=value('ssl.key')
    if cert and key: ctx.load_cert_chain(cert,key)
    selected=['manager.name','agent.id','id','timestamp','rule.id','rule.level','rule.description','rule.mitre','agent.name','agent.ip','data.srcip','data.srcuser','data.dstuser']
    body={'docs':[{'_index':r['index'],'_id':r['id'],'_source':selected} for r in refs]}
    auth=base64.b64encode((user+':'+password).encode()).decode()
    req=Request(host+'/_mget',data=json.dumps(body).encode(),headers={'Authorization':'Basic '+auth,'Content-Type':'application/json'},method='POST')
    with build_opener(ProxyHandler({}),HTTPSHandler(context=ctx),NoRedirect()).open(req,timeout=12) as response:
        content=response.read(2*1024*1024+1)
    if len(content)>2*1024*1024: raise ValueError()
    print(json.dumps(json.loads(content),allow_nan=False))
except Exception:
    print('SOURCE_READ_UNAVAILABLE',file=sys.stderr)
    sys.exit(1)
`;

export async function searchUidLookup(body: string): Promise<unknown> {
  const base = process.env.OPENSEARCH_URL || "http://localhost:9200";
  const endpoint = new URL(base);
  if (!["http:", "https:"].includes(endpoint.protocol) || endpoint.username || endpoint.password || endpoint.search || endpoint.hash) throw new Error("Invalid OpenSearch URL");
  const response = await fetch(`${base.replace(/\/$/, "")}/${LOOKUP_INDEX}/_msearch`, {
    method: "POST", headers: { "Content-Type": "application/x-ndjson" }, body,
    cache: "no-store", redirect: "error", signal: AbortSignal.timeout(5000),
  });
  if (!response.ok) throw new Error("UID lookup unavailable");
  if (!response.body) throw new Error("Lookup response body missing");
  const reader = response.body.getReader();
  const chunks: Uint8Array[] = [];
  let size = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > 2 * 1024 * 1024) {
        try { await reader.cancel(); } catch { /* Still fail closed. */ }
        throw new Error("Lookup response too large");
      }
      chunks.push(value);
    }
  } finally {
    reader.releaseLock();
  }
  return JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(Buffer.concat(chunks, size)));
}

export async function readUidSources(refs: SourceRef[]): Promise<unknown> {
  validateRefs(refs);
  if (!refs.length) return { docs: [] };
  const source = await resolveWazuhSource("wazuh.manager");
  if (!source.running || source.status !== "running") {
    throw new Error("Wazuh Manager is not running");
  }
  const encoded = Buffer.from(JSON.stringify(refs)).toString("base64");
  if (encoded.length > 60000) throw new Error("Source reference batch too large");
  const { stdout } = await exec("docker", ["exec", source.id, "python3", "-c", SOURCE_READER, encoded],
    { timeout: 16000, maxBuffer: 2 * 1024 * 1024, killSignal: "SIGTERM" });
  return JSON.parse(stdout);
}
