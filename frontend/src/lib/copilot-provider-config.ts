import { open, realpath } from 'node:fs/promises';
import { constants } from 'node:fs';
import { createLocalProvider, type LocalReservation } from './copilot-local-provider';
const ROOT='/mnt/nexus-copilot-mQTssj/';
async function privateText(path: string, max: number) {
  if (await realpath(path)!==path) throw Error('Private file path');
  const file=await open(path,constants.O_RDONLY|constants.O_NOFOLLOW);
  try {
    const stat=await file.stat();
    if (!stat.isFile() || stat.uid!==process.getuid?.() || (stat.mode&0o077)!==0 || stat.size>max) throw Error('Private file permissions');
    const buffer=Buffer.alloc(max+1);let size=0;
    while (size<buffer.length) {
      const part=await file.read(buffer,size,buffer.length-size,null);if(!part.bytesRead)break;size+=part.bytesRead;
    }
    if (size>max) throw Error('Private file size');
    return new TextDecoder('utf-8',{fatal:true}).decode(buffer.subarray(0,size));
  } finally {await file.close();}
}
// Reading this file does not issue a reservation or check other teams' GPU use.
// An operator must verify the shared GPU guard and create a fresh approved grant.
export function configuredLocalProvider() {
  return createLocalProvider({
    reservation:async()=>{
      const value=JSON.parse(await privateText(ROOT+'copilot-inference-reservation.json',4096));
      if (!value || typeof value!=='object' || Array.isArray(value) ||
        Object.keys(value).sort().join(',')!=='confirmed,expiresAt,gpuUuid,purpose,startsAt') throw Error('Reservation schema');
      return value as LocalReservation;
    },
    key:async()=>(await privateText(ROOT+'local-llm.secret',256)).trim(),
  });
}
