"""Prepare/build isolated empty-catalog preview. Does not start an HTTP service."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, importlib.util, io, json, os, re, shutil, socket, subprocess
import sys, tarfile, tempfile, urllib.request

REPO = Path('/home/saiuser/EDRXDR-Morpheus')
BASE = Path('/mnt/nexus-copilot-mQTssj')
STAGED = BASE / 'human-review-users-staged-56aiy2uv'
UNIT = 'nexus-all-events-prod-3006.service'
MANIFEST_SHA = '069be5199913db01995a0ae1fea1f4effdce22abdc08b38603945b1233ee62ba'

def need(ok, message):
    if not ok:
        raise RuntimeError(message)

def command(args, cwd=None):
    result = subprocess.run(args, cwd=cwd, capture_output=True, timeout=30)
    need(result.returncode == 0, 'Metadata command failed')
    return result.stdout

def show(key):
    return command(['systemctl', '--user', 'show', UNIT, '-p', key, '--value']).decode().strip()

def snapshot():
    return {key: show(key) for key in ('ActiveState', 'SubState', 'MainPID', 'WorkingDirectory')}

def private_bytes(path, maximum):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        need(info.st_uid == os.getuid() and info.st_nlink == 1
             and info.st_mode & 0o777 == 0o600 and info.st_size <= maximum,
             'Private registry metadata mismatch')
        raw = stream.read(maximum + 1)
        need(len(raw) <= maximum, 'Private registry size bound')
        return raw

def main():
    os.umask(0o077)
    need(os.geteuid() != 0, 'Run as ordinary user without sudo')
    before = snapshot()
    need(before['ActiveState'] == 'active' and before['SubState'] == 'running'
         and before['MainPID'].isdigit() and before['MainPID'] != '0', 'Production runtime unavailable')
    with socket.socket() as sock:
        need(sock.connect_ex(('127.0.0.1', 3013)) != 0, 'Preview port3013 occupied')
    need(shutil.disk_usage(BASE).free >= 2 * 1024**3, 'Need2GiB free for isolated build')
    matches = []
    for candidate in BASE.glob('review-integration-*/human-review-revision-integration'):
        manifest = candidate / 'candidate-sha256.json'
        if manifest.is_file() and hashlib.sha256(manifest.read_bytes()).hexdigest() == MANIFEST_SHA:
            matches.append(candidate)
    need(len(matches) == 1, 'Expected exactly one repaired tested candidate')
    candidate = matches[0]
    payload = json.loads((candidate / 'candidate-sha256.json').read_bytes())
    for name, digest in payload.items():
        relative = Path(name)
        need(not relative.is_absolute() and '..' not in relative.parts
             and hashlib.sha256((candidate / relative).read_bytes()).hexdigest() == digest,
             'Candidate source binding failed')
    for name, digest in json.loads((candidate / 'baseline-bindings.json').read_bytes()).items():
        need(hashlib.sha256(command(['git', 'show', 'HEAD:' + name], REPO)).hexdigest() == digest,
             'Committed source changed')
    node = Path('/proc/' + before['MainPID'] + '/exe').resolve(strict=True)
    active = Path(before['WorkingDirectory'])
    deps = active / 'node_modules'
    need(deps.is_dir() and not deps.is_symlink(), 'Expected independent active dependencies')
    for item in deps.rglob('*'):
        if item.is_symlink():
            target = Path(os.readlink(item))
            need(not target.is_absolute() and item.resolve().is_relative_to(deps.resolve()),
                 'External dependency symlink requires review')
    configs = [active / name for name in ('next.config.ts', 'next.config.js', 'next.config.mjs')
               if (active / name).is_file()]
    need(len(configs) == 1 and re.search(r'\bcpus[^:]{0,2}:\s*2\b', configs[0].read_text(encoding='utf-8')),
         'Active CPU-limited build configuration unavailable')
    users = private_bytes(STAGED / 'reviewers.json', 32768)
    sys.path.insert(0, str(candidate))
    import decision_review as legacy
    registry = legacy.parse_json(users, 503)
    try:
        legacy.principal('', registry, True)
    except legacy.Rejected as error:
        need(error.status == 401, 'Registry contract unavailable')
    need(any(user['role'] == 'reviewer' for user in registry['users']),
         'Named reviewer missing')
    root = Path(tempfile.mkdtemp(prefix='human-review-preview-prepared-', dir=BASE))
    print('PRIVATE_PREPARATION', root, flush=True)
    archive = command(['git', 'archive', 'HEAD', 'frontend'], REPO)
    need(len(archive) <= 32 * 1024**2, 'Source archive byte bound')
    with tarfile.open(fileobj=io.BytesIO(archive)) as stream:
        members = stream.getmembers()
        need(len(members) <= 3000 and sum(item.size for item in members) <= 32 * 1024**2,
             'Source archive size bound')
        for item in members:
            relative = Path(item.name)
            need(not relative.is_absolute() and '..' not in relative.parts
                 and relative.parts[0] == 'frontend' and (item.isdir() or item.isfile()),
                 'Source archive path/type rejected')
            target = root / relative
            if item.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open('xb') as output:
                    output.write(stream.extractfile(item).read())
    frontend = root / 'frontend'
    # Only reviewed candidate frontend sources are overlaid into the new isolated tree.
    for source in (candidate / 'frontend').rglob('*'):
        if source.is_file() and '__pycache__' not in source.parts:
            target = frontend / source.relative_to(candidate / 'frontend')
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    private = root / 'private-review'
    private.mkdir(mode=0o700)
    (private / 'reviewers.json').write_bytes(users)
    catalog = {'schema_version': 'nexus-human-review-v1',
               'generated_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
               'automated_response_allowed': False, 'items': []}
    raw = json.dumps(catalog, sort_keys=True).encode()
    pin = hashlib.sha256(raw).hexdigest()
    (private / ('catalog-' + pin + '.json')).write_bytes(raw)
    legacy.initialize(private, pin)
    bridge = frontend / 'src/lib/decision-review.ts'
    text = bridge.read_text(encoding='utf-8')
    old = "const ROOT = '/mnt/nexus-copilot-mQTssj/nexus-human-review-v1';"
    need(text.count(old) == 1, 'Candidate bridge root changed')
    bridge.write_text(text.replace(old, "const ROOT = '" + str(private) + "';"), encoding='utf-8')
    page = frontend / 'public/nexus/decision-review.html'
    html = page.read_text(encoding='utf-8')
    html = html.replace('<h1>ทบทวนแจ้งเตือน</h1>',
                        '<h1>PREVIEW · ทดสอบบัญชีผู้ทบทวน</h1>')
    html = html.replace('ตรวจหลักฐาน พิจารณาคำแนะนำ และบันทึกการตัดสินใจ',
                        'Catalog ว่าง · ยังไม่มีผลตรวจใหม่ที่รับรอง · ไม่ใช่ระบบ production')
    html = html.replace('href="./index.html">กลับ NEXUS',
                        'href="./decision-review.html">หน้า preview')
    page.write_text(html, encoding='utf-8')
    print('COPYING_EXISTING_DEPENDENCIES; no installation', flush=True)
    shutil.copytree(deps, frontend / 'node_modules', symlinks=True)
    # Preserve the active release build configuration with2workers, only in this copy.
    target_config = frontend / configs[0].name
    existing_configs = [frontend / name for name in
                        ('next.config.ts', 'next.config.js', 'next.config.mjs')
                        if (frontend / name).exists()]
    need(all(path == target_config for path in existing_configs), 'Build config type differs')
    shutil.copyfile(configs[0], target_config)
    cli = frontend / 'node_modules/next/dist/bin/next'
    help_text = command([str(node), str(cli), 'build', '--help'], frontend).decode()
    build = [str(node), str(cli), 'build']
    if '--webpack' in help_text:
        build.append('--webpack')
    print('ISOLATED_PREVIEW_BUILD_RUNNING; 2CPU/4GiB/10min maximum', flush=True)
    job = 'nexus-review-preview-build-' + root.name.rsplit('-', 1)[-1]
    args = ['systemd-run', '--user', '--quiet', '--wait', '--pipe', '--collect',
            '--unit=' + job, '--working-directory=' + str(frontend),
            '--property=CPUQuota=200%', '--property=MemoryMax=4G',
            '--property=TasksMax=256', '--property=RuntimeMaxSec=600',
            '--setenv=NEXT_TELEMETRY_DISABLED=1',
            '--setenv=NODE_OPTIONS=--max-old-space-size=3072'] + build
    with (root / 'build-private.log').open('wb') as log:
        result = subprocess.run(args, stdout=log, stderr=subprocess.STDOUT, timeout=660)
    need(result.returncode == 0 and (frontend / '.next/BUILD_ID').is_file(),
         'Build failed; preserve private log; no retry')
    need(snapshot() == before, 'Production runtime changed during preparation')
    plan = {'schema_version': 'named-review-empty-preview-plan-1',
            'production_before': before, 'frontend': str(frontend),
            'private_root': str(private), 'catalog_sha256': pin, 'catalog_items': 0,
            'registry_sha256_private': hashlib.sha256(users).hexdigest(),
            'named_users': len(registry['users']), 'node': str(node),
            'port': 3013, 'host': '127.0.0.1', 'maximum_seconds': 3600,
            'preview_started': False, 'production_changes': False,
            'build_id_sha256': hashlib.sha256((frontend / '.next/BUILD_ID').read_bytes()).hexdigest()}
    (root / 'preview-plan-private.json').write_text(json.dumps(plan, indent=2))
    print('EMPTY_CATALOG_PREVIEW_BUILD_PASS')
    print('NAMED_USERS', len(registry['users']), 'CATALOG_ITEMS 0')
    print('PREVIEW_PLAN', root / 'preview-plan-private.json')
    print('NOT_STARTED; production3006/observer/repo unchanged; no detector/model/GPU operations')

if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        safe = str(error) if type(error) is RuntimeError else type(error).__name__
        print('STOP_PREVIEW_PREPARATION', safe, '; no automatic retry; preserve private artifacts')
        raise SystemExit(1)
