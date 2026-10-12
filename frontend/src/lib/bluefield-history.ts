export type BluefieldRow = {
  id:string; timestamp:string; ibdev:string; interface:string; operstate:string; carrier:number|null;
  rx_packets:number; tx_packets:number; rx_bytes:number; tx_bytes:number; rx_errors:number; tx_errors:number;
  delta_rx_packets:number|null; delta_tx_packets:number|null; delta_rx_bytes:number|null; delta_tx_bytes:number|null; delta_rx_errors:number|null; delta_tx_errors:number|null;
  sample_interval_seconds:number|null; delta_status:Record<"rx_packets"|"tx_packets"|"rx_bytes"|"tx_bytes"|"rx_errors"|"tx_errors","first_sample"|"computed">;
};
type Obj=Record<string,unknown>;
export const BLUEFIELD_HISTORY_INDEX="review-bluefield-20261012t141653z-6396a0d3";
export const BLUEFIELD_FIELDS=["schema_version","processing_mode","production_ready","timestamp","event_type","source_type","measurement_scope","ibdev","interface","operstate","carrier","rx_packets","tx_packets","rx_bytes","tx_bytes","rx_errors","tx_errors","delta_rx_packets","delta_tx_packets","delta_rx_bytes","delta_tx_bytes","delta_rx_errors","delta_tx_errors","delta_status","sample_interval_seconds"] as const;
const obj=(v:unknown):v is Obj=>v!==null&&typeof v==="object"&&!Array.isArray(v);
const name=(v:unknown):v is string=>typeof v==="string"&&v.trim().length>0&&v.length<=256;
const date=(v:unknown):v is string=>typeof v==="string"&&Number.isFinite(Date.parse(v));
const count=(v:unknown):v is number=>typeof v==="number"&&Number.isFinite(v)&&Number.isSafeInteger(v)&&v>=0;
const interval=(v:unknown):v is number=>typeof v==="number"&&Number.isFinite(v)&&v>0;
const keys=["rx_packets","tx_packets","rx_bytes","tx_bytes","rx_errors","tx_errors"] as const;
export function parseBluefieldSearch(v:unknown):BluefieldRow[]{
  if(!obj(v)||v.timed_out!==false||!obj(v._shards)||v._shards.failed!==0||!obj(v.hits)) throw new Error("Incomplete search");
  const h=v.hits; if(!obj(h.total)||h.total.relation!=="eq"||!count(h.total.value)||!Array.isArray(h.hits)||h.total.value!==h.hits.length||h.hits.length>100) throw new Error("Incomplete result");
  const rows:BluefieldRow[]=[];
  for(const hit of h.hits){
    if(!obj(hit)||!name(hit._id)||!obj(hit._source)) throw new Error("Invalid hit"); const d=hit._source;
    if(d.schema_version!=="bluefield-normalized-review-1"||d.processing_mode!=="offline_review"||d.production_ready!==false||d.event_type!=="network_telemetry"||d.source_type!=="bluefield"||d.measurement_scope!=="host_interface_counters"||!date(d.timestamp)||!name(d.ibdev)||!name(d.interface)||!name(d.operstate)) throw new Error("Invalid identity");
    if(!(d.carrier===null||d.carrier===0||d.carrier===1)) throw new Error("Invalid carrier");
    for(const k of keys) if(!count(d[k])) throw new Error(`Invalid counter ${k}`);
    if(!obj(d.delta_status)) throw new Error("Missing delta status"); const status={} as BluefieldRow["delta_status"];
    for(const k of keys){ const s=d.delta_status[k], delta=d[`delta_${k}`]; if(s!=="first_sample"&&s!=="computed") throw new Error("Invalid delta status"); if(s==="first_sample"?delta!==null:!count(delta)) throw new Error("Delta/null mismatch"); status[k]=s; }
    const allFirst=Object.values(status).every(x=>x==="first_sample"), allComputed=Object.values(status).every(x=>x==="computed"); if(!allFirst&&!allComputed) throw new Error("Mixed delta status");
    if(allFirst&&d.sample_interval_seconds!==null) throw new Error("First interval must be null"); if(allComputed&&!interval(d.sample_interval_seconds)) throw new Error("Computed interval invalid");
    rows.push({id:hit._id,timestamp:d.timestamp,ibdev:d.ibdev,interface:d.interface,operstate:d.operstate,carrier:d.carrier,rx_packets:d.rx_packets as number,tx_packets:d.tx_packets as number,rx_bytes:d.rx_bytes as number,tx_bytes:d.tx_bytes as number,rx_errors:d.rx_errors as number,tx_errors:d.tx_errors as number,delta_rx_packets:d.delta_rx_packets as number|null,delta_tx_packets:d.delta_tx_packets as number|null,delta_rx_bytes:d.delta_rx_bytes as number|null,delta_tx_bytes:d.delta_tx_bytes as number|null,delta_rx_errors:d.delta_rx_errors as number|null,delta_tx_errors:d.delta_tx_errors as number|null,sample_interval_seconds:d.sample_interval_seconds as number|null,delta_status:status});
  }
  return rows.sort((a,b)=>Date.parse(a.timestamp)-Date.parse(b.timestamp)||a.interface.localeCompare(b.interface));
}
