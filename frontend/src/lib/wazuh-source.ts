import { execFile } from "node:child_process";
import { promisify } from "node:util";

const execute = promisify(execFile);
export type DockerReader = (args: string[]) => Promise<string>;
const readDocker: DockerReader = async args => {
  const { stdout } = await execute("docker", args, { timeout: 5000, maxBuffer: 1024 * 1024 });
  return stdout;
};
export class WazuhSourceError extends Error {}

// Resolve on each request. Never cache a name across container recreation.
export async function resolveWazuhSource(
  service: string,
  read: DockerReader = readDocker,
  project: string | undefined = process.env.WAZUH_COMPOSE_PROJECT,
) {
  if (!project || !/^[a-z0-9][a-z0-9_-]*$/.test(project)) {
    throw new WazuhSourceError("WAZUH_COMPOSE_PROJECT must identify the verified project");
  }
  const output = await read(["ps", "-a", "--no-trunc", "--filter",
    `label=com.docker.compose.project=${project}`, "--filter",
    `label=com.docker.compose.service=${service}`, "--format", "{{.ID}}"]);
  const ids = output.trim().split(/\r?\n/).filter(Boolean);
  if (ids.length !== 1 || !/^[a-f0-9]{64}$/.test(ids[0])) {
    throw new WazuhSourceError("Expected exactly one container in the configured project/service");
  }
  // Only request identity/state metadata, never environment values.
  const format = '{"id":{{json .Id}},"name":{{json .Name}},"project":{{json (index .Config.Labels "com.docker.compose.project")}},"service":{{json (index .Config.Labels "com.docker.compose.service")}},"running":{{json .State.Running}},"status":{{json .State.Status}}}';
  const data = JSON.parse(await read(["inspect", "--format", format, ids[0]]));
  if (data.id !== ids[0] || data.project !== project || data.service !== service ||
      typeof data.running !== "boolean" || typeof data.status !== "string" ||
      typeof data.name !== "string") {
    throw new WazuhSourceError("Container identity/state validation failed");
  }
  return { id: ids[0], name: data.name as string, project, service,
    running: data.running as boolean, status: data.status as string };
}
