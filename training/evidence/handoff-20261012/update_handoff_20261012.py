"""Verify VM evidence, back up documents, and record the Oct 12 handoff."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile

KAFKA = 'experiments/bluefield-kafka-runs/20261012T141233Z-beaccd98dc'
SEARCH = 'experiments/bluefield-opensearch-runs/20261012T141653Z-6396a0d3'
ARCHIVE = '20261012T135349958660Z'
MARK_START = '<!-- handoff-20261012-verified:start -->'
MARK_END = '<!-- handoff-20261012-verified:end -->'
DOCS = ('README.md', 'training/LATEST_STATUS.md', 'training/HANDOFF.md')

def require(ok, message):
    if not ok:
        raise RuntimeError(message)

def command(args):
    return subprocess.check_output(args, stdin=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                   timeout=25, text=True).strip()

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def insert(text, block):
    require(text.count(MARK_START) == text.count(MARK_END) <= 1, 'Invalid document markers')
    if MARK_START in text:
        before, rest = text.split(MARK_START, 1)
        _, after = rest.split(MARK_END, 1)
        return before + block + after
    lines = text.splitlines(keepends=True)
    if lines and lines[0].startswith('# '):
        return lines[0].rstrip() + '\n\n' + block + '\n\n' + ''.join(lines[1:]).lstrip('\n')
    return block + '\n\n' + text

def main():
    home = Path.home()
    repo = home / 'EDRXDR-Morpheus'
    archive = home / 'EDRXDR-Archive' / ARCHIVE
    require(repo.is_dir() and not repo.is_symlink(), 'Main repo missing or symlinked')
    k = json.loads((repo / KAFKA / 'report.json').read_text())
    s = json.loads((repo / SEARCH / 'report.json').read_text())
    manifest = json.loads((archive / 'manifest.json').read_text())
    require(k.get('status') == s.get('status') == 'PASS', 'Both PASS reports required')
    for report in (k, s):
        require(report.get('records') == 6 and report.get('carrier_null') == 6
                and report.get('first_sample_null') == 2 and report.get('computed_zero') == 4,
                'Unexpected report counts')
    require(k.get('record_bytes_equal') is True and k.get('normalized_equals_archived') is True
            and s.get('source_equal') is True, 'Equality verification missing')
    require(s.get('query_counts') == {'carrier_exists': 0, 'delta_exists': 4, 'delta_zero': 4, 'rx_zero': 6},
            'Query verification mismatch')
    require(sha(repo / KAFKA / 'received.jsonl') == k['received_sha256'] == k['input_sha256'] == s['input_sha256'],
            'Received record hash mismatch')
    require(sha(repo / KAFKA / 'normalized.jsonl') == s['normalized_sha256'], 'Normalized file hash mismatch')
    moves = manifest.get('moves', [])
    require(len(moves) == 7, 'Expected seven archive entries')
    for move in moves:
        src, dst = Path(move['from']), Path(move['to'])
        require(move['state'] == 'moved' and src.parent == home and archive in dst.parents
                and dst.exists() and not src.exists(), 'Archive state changed: ' + str(src))
    require((archive / 'organize_edrxdr_20261012.py').is_file(), 'Restore script missing')
    service = command(['systemctl', 'show', 'edrxdr-bluefield.service', '--no-pager',
                       '-p', 'ActiveState', '-p', 'SubState', '-p', 'UnitFileState'])
    require({'ActiveState=inactive', 'SubState=dead', 'UnitFileState=disabled'} <= set(service.splitlines()),
            'BlueField service state changed; inspect before documenting')
    branch = command(['git', '-C', str(repo), 'branch', '--show-current'])
    commit = command(['git', '-C', str(repo), 'rev-parse', 'HEAD'])
    before = command(['git', '-C', str(repo), 'status', '--short', '--untracked-files=all'])
    containers = command(['docker', 'ps', '--format', '{{.Names}}\t{{.Status}}\t{{.Image}}'])
    worktrees = command(['git', '-C', str(repo), 'worktree', 'list', '--porcelain'])
    now = datetime.now(timezone.utc).isoformat()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    detail_rel = 'training/HANDOFF-20261012-BLUEFIELD.md'
    evidence_rel = 'training/evidence/handoff-20261012'
    block = f'''{MARK_START}
## อัปเดตส่งต่อ 12 ต.ค. 2026 — BlueField และจัดเก็บไฟล์

- ตรวจหลักฐานและสถานะบน VM เมื่อ `{now}`; branch `{branch}`, commit `{commit}` ก่อนแก้เอกสาร
- Kafka replay PASS: ข้อมูลย้อนหลัง 6 แถว อ่านกลับ hash ตรง และ normalize ตรงกับหลักฐานเดิม
- OpenSearch index ทดลอง PASS: 6 แถวตรงทุกฟิลด์; carrier null 6, first-sample delta null 2, computed delta zero 4
- เป็นการทดสอบข้อมูลที่บันทึกไว้ทีละขั้น ไม่ใช่ continuous pipeline, live traffic, GPU inference หรือ model accuracy
- BlueField publisher: inactive/dead/disabled; หยุดวงจร restart แล้ว แต่ยังไม่ได้ซ่อม binary หรือคืนการส่ง telemetry
- ย้ายไฟล์/โฟลเดอร์สำรอง 7 รายการไป `~/EDRXDR-Archive/{ARCHIVE}/`; ไม่ลบข้อมูล ไม่ย้าย repo หลัก/personal worktree/โฟลเดอร์ BlueField
- รายละเอียด หลักฐาน คำสั่งกู้คืน และงานถัดไป: `{detail_rel}` (path จาก root repo)
- รายการที่ยังไม่เข้า Git และ container ที่กำลังทำงาน ณ เวลาอัปเดต: `{evidence_rel}/`
- งานถัดไป: ตรวจ frontend ล่าสุด แล้วเพิ่มมุมมอง BlueField แบบข้อมูลย้อนหลังจาก index ทดลอง; ยังไม่เปิด service หรือเชื่อม schema ทดลองเข้า live normalizer

อัปเดตนี้ใช้แทนข้อความเก่าที่บอกว่า BlueField ยังวน restart หรือยังไม่เคยทดสอบ Kafka/OpenSearch; ข้อความเก่าด้านล่างเก็บไว้เป็นประวัติ
{MARK_END}'''
    move_table = '\n'.join(f"| `{Path(m['from']).name}` | `{Path(m['to']).relative_to(archive)}` |" for m in moves)
    detail = f'''# ส่งต่องาน BlueField และจัดเก็บไฟล์ — 12 ตุลาคม 2026

ตรวจไฟล์รายงานจริงและสถานะระบบบน VM เมื่อ `{now}` (UTC)
Repo: `{repo}`; branch `{branch}`; commit `{commit}` ก่อนอัปเดตเอกสาร

## งานที่เสร็จและขอบเขต

1. จัดระเบียบไฟล์ 7 รายการ โดยย้ายเข้า archive และบันทึก manifest ไม่มีการลบหรือคืนพื้นที่ดิสก์
2. หยุดและ disable `edrxdr-bluefield.service` ที่เรียก binary หายและวน restart (ผู้ใช้พบ NRestarts=73095 ก่อนหยุด)
3. Kafka replay ผ่าน: ส่งข้อมูล BlueField ที่บันทึกไว้ 6 แถว อ่านกลับ bytes/hash ตรง และ normalize ตรงกับผลเดิม
4. OpenSearch ผ่าน: บันทึกผล normalize จากไฟล์ 6 แถว อ่านกลับ source ตรงครบ และ query แยก null จาก zero ได้

ข้อมูลเป็นสอง interface ที่ down, carrier อ่านไม่ได้จึง null และ counters เป็นศูนย์จริง ไม่ใช่หลักฐานว่า link ปกติหรือไม่มีภัยคุกคาม
DOCA ในงานทดลองใช้ค้นหาอุปกรณ์ ส่วน counters มาจาก Linux sysfs ไม่ใช่ DOCA Flow/packet capture
Kafka กับ OpenSearch ทดสอบแยกขั้นผ่านไฟล์ ยังไม่มี continuous consumer/indexer, live sampling หรือ dashboard integration ของ BlueField ในรอบนี้
ไม่ใช้ GPU ไม่เปลี่ยน driver/interface ไม่เปิด automated response และไม่มีผลประเมินคุณภาพโมเดลใหม่

## หลักฐานและปลายทาง

- Kafka report: `{KAFKA}/report.json`
- Kafka received/normalized JSONL และสคริปต์ที่ผ่าน: อยู่ในโฟลเดอร์เดียวกับ report
- Kafka topic: `{k['topic']}` บน `edrxdr-replay-kafka-1`; แยก topic แต่ใช้ broker/resource ร่วม
- ข้อความ topic ใหม่ตั้ง retention 1 วัน; topic ไม่ถูกลบอัตโนมัติ และการล้างข้อความไม่จำเป็นต้องตรงเวลา 24 ชั่วโมงพอดี
- รอบ Kafka แรก FAIL ก่อนสร้าง topic: `experiments/bluefield-kafka-runs/20261012T140620Z-f8769c8cdb/`; รอบที่ผ่านปรับ stdin และใช้ docker exec -i เฉพาะ producer
- OpenSearch report: `{SEARCH}/report.json`
- OpenSearch index: `{s['index']}` บน `edrxdr-replay-opensearch-1`; ไม่มีการตั้งลบ index อัตโนมัติ
- Index ทดลองใช้ 1 primary / 0 replicas เฉพาะ index นี้ ไม่แก้ cluster หรือ index เดิม
- Raw SHA256: `{s['input_sha256']}`
- Normalized SHA256: `{s['normalized_sha256']}`
- ผล: records 6; carrier null 6; first delta null 2; computed zero 4
- Query counts: carrier_exists 0; rx_zero 6; delta_exists 4; delta_zero 4
- รายงานเป็นผลการรันทดสอบก่อนหน้านี้ที่ตรวจไฟล์/hash ในรอบส่งต่อ ไม่ได้รัน integration ซ้ำขณะอัปเดตเอกสาร

## การจัดเก็บไฟล์นอก repo

Archive: `{archive}`

| ตำแหน่งเดิมใต้ home | ตำแหน่งใหม่ใต้ archive |
|---|---|
{move_table}

`manifest.json` บันทึก from/to/state ของแต่ละรายการ; ตรวจว่าปลายทางยังมีอยู่และต้นทางไม่มีแล้ว
`EDRXDR-HANDOFF` ว่างตอนย้ายตามเงื่อนไข organizer ส่วน dashboard-review เป็นโฟลเดอร์ตรวจรุ่นเก่า
ไฟล์ backups เก็บย้อนกลับ, packages เก็บ zip ที่เคยส่ง; การย้ายไม่ได้พิสูจน์ว่า backup ทุกชุดกู้ได้สมบูรณ์
คง `~/EDRXDR-Morpheus`, `~/EDRXDR-Morpheus-personal` (linked Git worktree), โฟลเดอร์ทดลอง BlueField, hidden config, venvs และ Docker volumes ไว้ตำแหน่งเดิม
บางโฟลเดอร์เก่าอาจอ้าง absolute path เดิม จึงควรกู้คืนก่อนนำ build เก่ากลับมารัน

คำสั่งนี้ใช้เฉพาะเมื่อต้องการย้ายกลับ ไม่ต้องรันเพื่อทำงานต่อ:

```bash
python3 {archive}/organize_edrxdr_20261012.py --restore {archive}/manifest.json
```

ต้นฉบับหลักฐาน BlueField ที่ยังเก็บไว้:
- `~/edrxdr-bluefield-nullcheck.Bn44DZ` — monitor run
- `~/edrxdr-bluefield-normalize.udX6v2` — offline normalization run
- `~/edrxdr-bluefield-review.9F1hBG` — experimental monitor source
สคริปต์ส่งผ่าน `/tmp` เป็นไฟล์ชั่วคราว; ใช้สำเนาใน archive/โฟลเดอร์ผลทดสอบเพื่อเก็บระยะยาว
งานนี้ไม่ได้ย้าย dataset/model Docker volumes; อ้างตำแหน่งจาก HANDOFF เดิมและตรวจ mounts จริงก่อนใช้

## ปัญหาคงเหลือและงานถัดไป

1. เพิ่มหน้า/ส่วน BlueField บน Dashboard จาก index ทดลองนี้ โดยอ่าน frontend ปัจจุบันก่อนแก้ เนื่องจาก Windows กับ VM อาจอยู่ต่าง commit
2. ต้องแสดง archived batch, เวลาตัวอย่างจริง, interface down, carrier unknown และ first-sample delta N/A; ห้ามแปลง null เป็น zero/healthy
3. Live normalizer เดิมแปลง null เป็น zero จึงยังไม่ส่ง schema ทดลองไป `bluefield-events` หรือ `morpheus-input`
4. Publisher binary ที่ service เรียกยังหาย; service ถูก stop/disable เพื่อหยุด restart loop เท่านั้น ยังไม่ deploy binary ใหม่หรือ enable service
5. ยังไม่มี live traffic, GPU parity, outage/recovery หรือ production-readiness validation ของ BlueField
6. เก็บเอกสาร/สคริปต์/หลักฐานเข้า Git หลังตรวจรายการและข้อมูลที่ไม่ควรเผยแพร่; สคริปต์อัปเดตนี้ไม่ commit/push

เริ่มงานต่อด้วยคำสั่งอ่านสถานะ:

```bash
cd ~/EDRXDR-Morpheus || exit 1
git branch --show-current
git log -1 --oneline
git status --short
systemctl show edrxdr-bluefield.service --no-pager -p ActiveState -p SubState -p UnitFileState
docker ps --format 'table {{{{.Names}}}}\\t{{{{.Status}}}}\\t{{{{.Image}}}}'
cat {KAFKA}/report.json
cat {SEARCH}/report.json
docker exec edrxdr-replay-opensearch-1 curl -fsS --max-time 15 'http://localhost:9200/{s['index']}/_count?pretty'
```

ก่อนแก้ Dashboard ให้อ่าน `frontend/package.json`, `frontend/src/app/api/shadow/`, `frontend/src/app/shadow/` และ `frontend/src/lib/shadow.ts` จาก checkout จริง
ใช้ index ระบุชื่อชัดเจน ไม่ใช้ wildcard รวม Live/Replay/Shadow; ตรวจ output contracts และรัน tests/typecheck/build ตาม package.json จริง

## Snapshot ส่งต่อ

`{evidence_rel}/` เก็บรายงาน Kafka/OpenSearch สำเนา manifest, service-state.txt, containers.txt, worktrees.txt และ Git status ก่อน/หลังแก้เอกสาร
Snapshot เป็นสถานะขณะบันทึก ไม่รับรองว่าบริการยังอยู่สถานะเดียวกันเมื่อเพื่อนเริ่มงาน
ไม่รวม model weights, credentials หรือฐาน OpenSearch ทั้งชุด
'''
    writes = {repo / d: insert((repo / d).read_text(encoding='utf-8'), block) for d in DOCS}
    writes[repo / detail_rel] = detail
    results = repo / 'experiments/bluefield-review-20261012/RESULTS.md'
    writes[results] = insert(results.read_text(encoding='utf-8'), block)
    for path in writes:
        require(not path.is_symlink(), 'Refuse symlink document: ' + str(path))
    backup_dir = home / 'EDRXDR-Archive' / 'documentation-backups'
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / f'handoff-before-{stamp}.tar.gz'
    evidence_dir = repo / evidence_rel
    with tarfile.open(backup, 'x:gz') as archive_file:
        for path in writes:
            if path.exists():
                archive_file.add(path, arcname=str(path.relative_to(repo)))
        if evidence_dir.exists():
            archive_file.add(evidence_dir, arcname=evidence_rel)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    for name, data in {'kafka-report.json': k, 'opensearch-report.json': s, 'archive-manifest.json': manifest}.items():
        (evidence_dir / name).write_text(json.dumps(data, indent=2), encoding='utf-8')
    for name, value in {'service-state.txt': service, 'containers.txt': containers, 'worktrees.txt': worktrees,
                        'git-status-before.txt': before, 'commit.txt': commit, 'verified-utc.txt': now}.items():
        (evidence_dir / name).write_text(value + '\n', encoding='utf-8')
    for path, text in writes.items():
        path.write_text('\n'.join(line.rstrip() for line in text.splitlines()) + '\n', encoding='utf-8')
    (evidence_dir / 'update_handoff_20261012.py').write_bytes(Path(__file__).read_bytes())
    (evidence_dir / 'git-status-after.txt').touch(exist_ok=True)
    (evidence_dir / 'git-status-after.txt').write_text(command(['git', '-C', str(repo), 'status', '--short', '--untracked-files=all']) + '\n', encoding='utf-8')
    print('Backup:', backup)
    print(command(['git', '-C', str(repo), 'diff', '--check', '--', *DOCS, str(results.relative_to(repo))]))
    print('PASS: updated README, LATEST_STATUS, HANDOFF, BlueField RESULTS and detailed handoff; evidence snapshots saved.')
    print('No service changes, file relocation, commit or push performed.')
    print('Read:', repo / detail_rel)

if __name__ == '__main__':
    main()
