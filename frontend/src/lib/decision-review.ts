import { execFile } from 'node:child_process';
import { resolve } from 'node:path';

export type DecisionWorkerRequest = {
  method: 'GET' | 'POST'; authorization: string; body: unknown;
};
export type DecisionWorkerResponse = { status: number; body: Record<string, unknown> };
const ROOT = '/mnt/nexus-copilot-mQTssj/nexus-human-review-v1';

export function runDecisionReview(input: DecisionWorkerRequest, catalogHash: string): Promise<DecisionWorkerResponse> {
  if (!/^[a-f0-9]{64}$/.test(catalogHash)) return Promise.reject(Error('Unpinned catalog'));
  return new Promise((accept, reject) => {
    // Credentials go through stdin, never shell arguments, environment or logs.
    const child = execFile('python3', ['-B', resolve(process.cwd(), 'server/decision_review.py'),
      '--root', ROOT, '--catalog-sha256', catalogHash], {
      timeout: 8000, maxBuffer: 16 * 1024 * 1024, encoding: 'utf8', windowsHide: true,
    }, (error, stdout) => {
      if (error) { reject(Error('Decision worker unavailable')); return; }
      try {
        const result = JSON.parse(stdout);
        if (!result || ![200, 400, 401, 403, 404, 409, 413, 503].includes(result.status) ||
          !result.body || typeof result.body !== 'object' || Array.isArray(result.body)) throw Error();
        accept(result);
      } catch { reject(Error('Decision worker invalid response')); }
    });
    child.stdin?.on('error', () => reject(Error('Decision worker unavailable')));
    child.stdin?.end(JSON.stringify(input));
  });
}
