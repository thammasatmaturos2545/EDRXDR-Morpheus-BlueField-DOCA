> Latest scope and takeover guide: [Company scope handoff](HANDOFF-COMPANY-SCOPE-20261014.md). Verified rehearsal results remain unchanged; earlier sections retain historical context.

> Latest rehearsal: [14 Oct 5/5/5](HANDOFF-REHEARSAL-20261014.md) — verified Windows origin, API/UI and clean exit after supervisor update. Earlier results remain historical.

> Latest handoff: [HANDOFF-NEXT-20261014.md](HANDOFF-NEXT-20261014.md). Code checkpoint 8f737f9; supervisor cfecdcf offline tests and updated demo UI recorded. Sections below retain historical scope and reservation dates; follow the latest handoff before running commands.

> Latest checkpoint: see training/HANDOFF-DEMO-CLOSE-20261014.md. Run d20261013t181858-e1bbae7e: 2/2/2, container and launcher exit 0; API and operator UI observation verified. Earlier exit 124 remains historical.

<!-- severity-flow-verified-20261013 -->
> อัปเดต13ต.ค.: ทดสอบ Windows Agent004 → Kafka → Morpheus Severity GPU → OpenSearch → Dashboard แล้วใน bounded microbatch run `d20261013t164314-c1b4d787`; counts3/3/3 ตรวจต้นทางWindowsหนึ่งรายการด้วยUID/hash ผ่าน และworker_stoppedแล้ว รายงานexitcodeดูเอกสารใหม่ ห้ามอ้างexit0โดยไม่มีหลักฐาน สถานะก่อนหน้านี้ที่ระบุว่ายังไม่ได้เดโมครบสายเป็นประวัติ อ่าน [ส่งต่อรอบล่าสุด](HANDOFF-SEVERITY-FLOW-20261013.md) ก่อนทำงานต่อ

# Source review update — 11 ต.ค. 2026 (ยังไม่ใช่การรันใหม่บน VM)

<!-- step8-vm-close-20261013 -->
## Step 8 — VM checkpoint closed for progress presentation

- VM synthetic operator tests: 123/123 PASS.
- Read-only OpenSearch preflight: deployment_checked, exit code 0.
- No quarantine indices were present at inspection.
- Exact quarantine-document retrieval remains UNVERIFIED on the VM.
- This is not an end-to-end quarantine replay or production-readiness PASS.
- No additional fixture was created; replay remains unauthorized.
- Tests: `training/evidence/bluefield-operator-step8-20261013T072419032202Z/validation.txt`
- Preflight and exit code: `training/evidence/bluefield-sink-preflight-mRy7AERJ/`
- Scope freeze for the 16 October progress presentation: record this limitation;
  proceed to Dashboard/demo preparation. Defer new fixtures and replay integration.



<!-- operator-cb514aa-status:start -->
## Latest operator checkpoint — 13 ต.ค. 2026 / cb514aa

Operator tooling implemented through step 7: offline canonical review/journal binding for synthetic fixtures. Step 6 real Kafka fixture source-reader PASS; no real quarantine replay or operational approval issued in that fixture. Local source review: 109 synthetic operator tests PASS (Windows; not a new VM integration run).

Read `training/HANDOFF-OPERATOR-20261013.md` (repository-root path) for current scope, evidence and next steps. Earlier sections saying operator tooling is not implemented are historical; transport for real quarantine remains unimplemented. BlueField service was last reported inactive/dead/disabled; recheck before work.

This documentation update does not enable transport, issue approval, run fixtures, move files, or change services. Prior seven-item archive organization is retained and described in the detailed handoff.
<!-- operator-cb514aa-status:end -->


<!-- handoff-20261012-verified:start -->
## อัปเดตส่งต่อ 12 ต.ค. 2026 — BlueField และจัดเก็บไฟล์

- ตรวจหลักฐานและสถานะบน VM เมื่อ `2026-10-12T14:24:50.161605+00:00`; branch `work/shadow-mode-v1`, commit `6ba5bf95ba00ee1dcf4d47728090ae7eb1b251c8` ก่อนแก้เอกสาร
- Kafka replay PASS: ข้อมูลย้อนหลัง 6 แถว อ่านกลับ hash ตรง และ normalize ตรงกับหลักฐานเดิม
- OpenSearch index ทดลอง PASS: 6 แถวตรงทุกฟิลด์; carrier null 6, first-sample delta null 2, computed delta zero 4
- เป็นการทดสอบข้อมูลที่บันทึกไว้ทีละขั้น ไม่ใช่ continuous pipeline, live traffic, GPU inference หรือ model accuracy
- BlueField publisher: inactive/dead/disabled; หยุดวงจร restart แล้ว แต่ยังไม่ได้ซ่อม binary หรือคืนการส่ง telemetry
- ย้ายไฟล์/โฟลเดอร์สำรอง 7 รายการไป `~/EDRXDR-Archive/20261012T135349958660Z/`; ไม่ลบข้อมูล ไม่ย้าย repo หลัก/personal worktree/โฟลเดอร์ BlueField
- รายละเอียด หลักฐาน คำสั่งกู้คืน และงานถัดไป: `training/HANDOFF-20261012-BLUEFIELD.md` (path จาก root repo)
- รายการที่ยังไม่เข้า Git และ container ที่กำลังทำงาน ณ เวลาอัปเดต: `training/evidence/handoff-20261012/`
- BlueField Historical Dashboard integration เสร็จและตรวจแล้ว; งานถัดไปคือรักษา historical/non-live semantics, review หลักฐาน และยังไม่เปิด service หรือเชื่อม schema ทดลองเข้า live normalizer

อัปเดตนี้ใช้แทนข้อความเก่าที่บอกว่า BlueField ยังวน restart หรือยังไม่เคยทดสอบ Kafka/OpenSearch; ข้อความเก่าด้านล่างเก็บไว้เป็นประวัติ
<!-- handoff-20261012-verified:end -->

ตรวจชุด `edrxdr-shadow-review.tar.gz` และเตรียม patch ในเครื่องผู้ช่วยแล้ว:
- Persist ค่า HOME/XDG/CUPY/CUDA cache ใน Compose; gate ทั้งสองยังเป็น 0, ไม่มี daemon/restart policy ใหม่.
- เพิ่มการตรวจ acknowledgement ของ indexer ก่อน commit offset และ tests สำหรับ retry แบบ isolated.
- ตรวจ API/หน้า Shadow ให้ AE state/coverage สอดคล้องกัน, รักษา unknown Wazuh level และไม่ส่ง nested metadata ที่ไม่ผ่านการตรวจไป browser.
- Frontend Shadow 20 checks, regression 7 groups, TypeScript และ lint ผ่าน locally.
- Recovery tests 7 ผ่านด้วย fake clients/stub validator; ไม่ใช่ real Kafka/OpenSearch outage test.
- Worker suite เดิมยังตรวจไม่ครบ locally เพราะ archive ไม่รวม replay validators ที่ source-lock pin ไว้.
  ไม่แก้ pins และไม่ถือ full suite ว่าผ่าน. ต้องรันบน checkout จริงที่มี source ครบ.
- Production build รอบนี้ติด Windows SWC access denial; ผล build/VM ของรุ่นใหม่ยังไม่ยืนยัน.

หลักฐานเดิม: stored batch 32/32, candidates13 (รายงานว่า rule19008 ทั้งหมด), AE-scored0, novelty1.
ข้อมูลนี้ไม่ใช่ accuracy/FPR หรือหลักฐานบริการสดกำลังทำงาน. การประเมิน text/source distribution
และ replay-vs-shadow score parity ยังต้องใช้ข้อมูล/โมเดลจริงที่ไม่ได้แนบมา.

หลังติดตั้ง patch ให้รัน `bash verify_shadow_review.sh` เพื่อเก็บ CPU/source-pin/config checks บน VM.
สคริปต์ไม่เปิด container, GPU, web server หรือ training. ไม่ต้องเปิด daemon เพื่อเติมข้อมูล Dashboard.
ดู [รายละเอียด review และข้อจำกัด](../shadow/REVIEW.md). source-lock/scoring/model/threshold ไม่เปลี่ยน.
ยังไม่ได้ commit/push หรือเปลี่ยน runtime บน VM จากการ review ครั้งนี้.

---

## บันทึกก่อนรอบ source review (เก็บไว้เป็นประวัติ ไม่ใช่สถานะปัจจุบัน)

# Handoff — resume bounded Shadow work

<!-- DASHBOARD_HANDOFF_20261011 -->
## อัปเดตส่งต่อ 11 ต.ค. 2026 — Dashboard Shadow ใช้งานได้แล้ว

อัปเดตนี้ใช้ผล terminal และภาพหน้าเว็บที่ผู้ใช้ส่งหลังติดตั้ง Dashboard;
ข้อมูล audit เวลา 02:32 ด้านล่างเป็นประวัติก่อนเพิ่มหน้าเว็บ ไม่ใช่สถานะบริการปัจจุบัน.

- หน้า `http://172.16.30.147:3000/shadow` เปิดได้และอ่านข้อมูลจริงจาก Replay OpenSearch.
- API `/api/shadow/events`: severity32, behavioral32, matched32, conflicts0, unmatched0,
  candidates13, ae_scored0, novelty1. Candidate ทั้ง13รายการเป็น rule19008 (Wazuh level3).
- ตัวกรอง Severity candidates และรายละเอียด source offset / model / hash แสดงได้ตามภาพ.
- เป็น stored Shadow batch ไม่ใช่ live inference ต่อเนื่อง; 32/32 เป็นความครบถ้วนของข้อมูล ไม่ใช่ accuracy.
- Branch ล่าสุดที่ตรวจ `work/shadow-mode-v1`, HEAD `12d6049741235ba4bb45d65c1e3f59d4e01ce5b3`.
  ยังไม่มีหลักฐาน commit/push ใหม่. ต้องอ่าน `git status` อีกครั้งก่อนรับช่วงต่อ.
- Frontend รัน foreground บน port3000 ตามผลล่าสุด; อายุ process หลัง logout ไม่รับประกัน.
  ไม่ได้เปิด GPU เพื่อทำหน้าเว็บ และไม่ได้เปลี่ยน Kafka/OpenSearch/model.

### การทดสอบ: แยกผลที่ยืนยันแล้วกับงานค้าง

| รายการ | หลักฐาน / สถานะ |
|---|---|
| Shadow worker CPU contracts | VM 23 PASS จาก audit เดิม |
| Frontend Shadow tests | VM 14 PASS ก่อน build; ใช้ synthetic fixtures ไม่ใช่ model quality |
| Frontend typecheck | VM ผ่านใน output ที่ส่งมา |
| Full regression ครั้งแรก | 5 groups ผ่าน แล้วล้มเพราะ test จับ request สุดท้ายผิด index |
| Regression fix | แก้ tests/regression.cjs ให้ตรวจ requests แยกตาม URL; targeted test และ lint ผ่านในเครื่องผู้ช่วย |
| Full regression หลังแก้บน VM | ยังไม่ได้รับ output ยืนยันครบ ห้ามลงว่า PASS |
| Production build | local PASS; VM เสิร์ฟ /shadow ได้แล้ว แต่ยังไม่ได้รับ build log ยืนยันครบ |
| Browser / actual API | ผู้ใช้ส่งภาพและผล API ยืนยัน 32/32 พร้อม candidate rule19008 ทั้ง13 |

### ไฟล์งานล่าสุด

แก้ `frontend/src/app/dashboard.tsx` เพิ่มลิงก์ Shadow และ `frontend/tests/regression.cjs`
แก้ test ที่เก็บ query เดียวแม้ Replay API อ่านสอง index. ไม่แก้ live/replay API เดิม.
เพิ่ม `frontend/src/lib/shadow.ts`, `frontend/src/app/shadow/page.tsx`,
`frontend/src/app/api/shadow/events/route.ts`, `frontend/tests/shadow.cjs`,
`frontend/run_shadow_dashboard.sh`, `frontend/SHADOW_DASHBOARD.md`.
ยังต้อง review/stage `shadow/`, `training/evidence/` และเอกสารที่แก้; ไม่ใช้ git add . แบบไม่ตรวจ.

### สิ่งที่เพื่อนต้องทำต่อ (เรียงลำดับ)

1. เก็บผล full regression/typecheck หลังแก้ลงไฟล์ เพื่อปิดช่องว่างหลักฐาน; build ซ้ำเฉพาะจำเป็น
   โดยหยุด frontend ของตัวเองก่อน ไม่หยุดบริการร่วม.
2. วิเคราะห์ rule19008 จากข้อมูลที่อนุญาต: text ที่โมเดลอ่าน, Wazuh label และ source distribution.
   13 candidates คือ disagreement ไม่ใช่ confirmed attacks/FP. อย่า tune threshold จาก batch นี้ทันที.
3. เลือกเคส Replay ที่มีคะแนน AE จริงเพื่อนำเสนอแยกจาก Shadow ซึ่ง AE coverage0;
   ตรวจข้อมูลก่อนอ้างผล และรักษา old-test/reserve ไว้.
4. Persist cache env ใน Shadow Compose และปรับ shadow/README.md / PACKAGE_SHA256 ที่ยังเก่า.
5. ตรวจ Git/เอกสาร บันทึกเวอร์ชันเดโมเมื่อได้รับคำสั่ง commit; ซ้อมและอัดวิดีโอก่อนนำเสนอ 16 ต.ค.
6. งานหลังเดโม: replay-vs-shadow score parity ของ input เดียวกัน, isolated recovery tests,
   pagination/retention และการออกแบบบริการต่อเนื่อง. ยังไม่เปิด automated response.

### เปิดเว็บและตรวจผล (CPU เท่านั้น)

```bash
cd ~/EDRXDR-Morpheus || exit 1
date -Is
git branch --show-current
git log -1 --oneline
git status --short --untracked-files=all
git diff --check
ss -ltn | grep ':3000' || true
```

หาก port3000 ยังว่าง ให้เปิดใน terminal แยก:

```bash
cd ~/EDRXDR-Morpheus/frontend || exit 1
bash run_shadow_dashboard.sh
```

Runner หา IP ปัจจุบันของ `edrxdr-replay-opensearch-1` บน `edrxdr-replay_replay-net`,
ตรวจ count ทั้งสอง index แล้วตั้ง `SHADOW_OPENSEARCH_URL` ก่อนเปิด Next.js.
VM ทดสอบเส้นทางนี้อ่าน count32/32 สำเร็จแล้ว. ไม่ใช้ localhost:9200 แทน เพราะนั่นคือ live OpenSearch.
Runner ไม่ตั้ง `REPLAY_OPENSEARCH_URL`; หน้า /replay ต้องตรวจ config ของตัวเอง.
Ctrl+C หยุดเฉพาะเว็บ. ไม่ต้อง retrain, restart agent หรือเปิด GPU เพื่อดูผลที่บันทึกไว้.

ตรวจ API จากอีก terminal และเก็บเฉพาะ summary (ไม่มี raw logs):

```bash
cd ~/EDRXDR-Morpheus || exit 1
python3 - <<'PY'
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen
with urlopen('http://127.0.0.1:3000/api/shadow/events', timeout=20) as r:
    data = json.load(r)
events = data['events']
report = {
    'checked_at': datetime.now(timezone.utc).isoformat(),
    'counts': data['counts'],
    'candidates_by_rule': dict(Counter(str(e['severity']['wazuh_rule_id'])
        for e in events if e.get('severity') and e['severity'].get('false_positive_candidate') is True)),
    'join_states': dict(Counter(e['status'] for e in events)),
    'scope': 'Dashboard API observation; not model quality or full regression evidence',
}
p = Path('training/evidence/dashboard-20261011')
p.mkdir(parents=True, exist_ok=True)
target = p / ('api-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
with target.open('x') as f:
    json.dump(report, f, indent=2)
print(json.dumps(report, indent=2))
print('Saved:', target)
PY
```

เก็บผล tests โดยไม่ใช้ GPU ไม่ต้องหยุดหน้าเว็บ:

```bash
(
set -euo pipefail
cd ~/EDRXDR-Morpheus/frontend
evidence_dir=../training/evidence/dashboard-20261011
mkdir -p "$evidence_dir"
stamp=$(date -u +%Y%m%dT%H%M%SZ)
node tests/shadow.cjs 2>&1 | tee "$evidence_dir/shadow-tests-$stamp.txt"
npm run typecheck 2>&1 | tee "$evidence_dir/typecheck-$stamp.txt"
npm run test:regression 2>&1 | tee "$evidence_dir/regression-$stamp.txt"
)
```

### รายงานและไฟล์นอก repo ของรอบ Dashboard

- `training/evidence/dashboard-20261011/reported-result.json`: สรุปผลที่ผู้ใช้ส่ง ไม่ใช่การรันใหม่โดย installer.
- `training/evidence/shadow-20261011/`: audit เดิมและ join evidence ของ batch32.
- `edrxdr-shadow_shadow-state:/join-check-20261010T192035112516Z.json`: join report ต้นฉบับ.
- `/tmp/edrxdr-dashboard-source-SU6Qhaeb.tar.gz`: frontend snapshot ก่อนเพิ่ม Shadow.
- `/tmp/edrxdr-shadow-dashboard-20261011.tar.gz`: patch หน้า/API Shadow รุ่นแรก;
  ต้องมี regression fix แยกด้วย ไม่ใช่ชุดล่าสุดครบใน archive เดียว.
- `/tmp/regression-shadow-fix-20261011.cjs`: test fix ที่ส่งภายหลัง.
- `/tmp/edrxdr-before-shadow-dashboard-20261011T140228652744Z.tar.gz`: backup ไฟล์ก่อนแก้ Dashboard.
- `/tmp/regression-before-fix-*.cjs`: backup test ถ้ารันสคริปต์แก้ตามที่ให้.
- `/tmp/edrxdr-docs-before-20261010T193733563462Z.tar.gz`: backup docs ก่อน update รอบแรก.

หน้า Shadow รับสูงสุด500 documents ต่อ index และปฏิเสธ partial/duplicate results;
สอง index ไม่ได้อ่านเป็น atomic snapshot ต้อง refresh หลังจบ batch.
เก็บข้อมูลใน Docker volumes ตาม audit เดิม ไม่เพิ่ม weights/dataset/raw events เข้า Git.
จองเครื่อง 11 ต.ค. ถึง24:00 ไม่ใช่สิทธิ์ใช้งานวันถัดไป; ตรวจการจองก่อนรัน GPU ใหม่.

---

## ข้อมูลอ้างอิงจาก audit ก่อนเพิ่ม Dashboard

ส่วนต่อไปเก็บผลและข้อจำกัด ณ 02:32 ไว้ตามเดิม โดยข้อความที่บอกว่า Dashboard ยังไม่ตรวจ
ถูกแทนที่ด้วยผลยืนยันด้านบน. ตำแหน่ง model/dataset และข้อจำกัดคุณภาพยังใช้เป็นจุดเริ่มตรวจต่อได้.

สถานะอ้างอิง VM ณ `2026-10-11T02:32:23+07:00`; branch `work/shadow-mode-v1`,
base commit `12d6049741235ba4bb45d65c1e3f59d4e01ce5b3`.

**Bounded Shadow pilot ผ่าน 32/32 เหตุการณ์แล้ว และหยุดหลังจบรอบ ไม่ใช่บริการต่อเนื่องหรือ production-ready**
Severity เป็น weakly supervised Wazuh severity baseline ไม่ใช่ independent threat detector หรือ attack probability.
Automated response / containment: **OFF**. Behavioral novelty ไม่ได้แปลว่าเป็นการโจมตี;
not-scored ไม่ได้แปลว่าปลอดภัย.


อ่าน [LATEST_STATUS.md](LATEST_STATUS.md) สำหรับผล รายงาน volumes/container และ inventory นอก repo;
เอกสารนี้ให้คำสั่งรับช่วงต่อ. ไม่มี commit/push หรือเปลี่ยน runtime จากการอัปเดต docs ครั้งนี้.

## 1. ตรวจสถานะก่อนทำงาน

```bash
cd ~/EDRXDR-Morpheus || exit 1
date -Is
git branch --show-current
git log -1 --oneline
git status --short --untracked-files=all
git diff --check
docker ps --format 'table {{.Names}}	{{.Status}}	{{.Ports}}'
docker compose -f shadow/compose.yml config --quiet
docker compose -f shadow/compose.yml run --rm \
  --entrypoint /opt/conda/envs/morpheus/bin/python \
  inspect -B /shadow/test_shadow.py
docker compose -f shadow/compose.yml run --rm inspect
```

Tests ล่าสุด 23 PASS. Preflight อ่าน metadata/model/health และเขียน audit ของตัวเอง;
ไม่ใช้ GPU/สร้าง topics/เปลี่ยน offsets. หาก source hash เปลี่ยน ห้ามแก้ source-lock ให้ผ่านโดยไม่ review.
`shadow/README.md` เดิมยังเล่าเหตุการณ์ก่อนแก้สำเร็จ ให้ใช้สถานะล่าสุดในเอกสารนี้.

## 2. ตรวจผลที่มีอยู่โดยไม่สร้างรอบใหม่

```bash
for kind in severity behavioral; do
  docker exec edrxdr-replay-opensearch-1 curl -fsS --max-time 15 \
    "http://localhost:9200/shadow-$kind-v1/_count"
done
docker exec edrxdr-replay-kafka-1 timeout 20s \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server kafka:29092 --all-groups --describe
docker exec edrxdr-kafka timeout 20s \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server 172.16.30.147:9092 --group edrxdr-shadow-copy-v1 --describe
docker compose -f shadow/compose.yml run --rm \
  --entrypoint /bin/sh inspect -c \
  'cat /shadow-state/join-check-20261010T192035112516Z.json'
```

Baseline: indexes32/32, join32/32, rawhash32/32; severity candidates13, AE-scored0, novelty1.
Capture commit15605; audit end15854/lag249. สี่ downstream groups offset32/end32/lag0.
ไม่มี active members เป็นปกติหลัง finite job เสร็จ. จำนวนอาจเปลี่ยนหากเพื่อนทำรอบใหม่.
รายงานเดิมพิสูจน์เฉพาะ batch เดิม; ห้ามใช้ count32 assertion กับรอบที่เพิ่มข้อมูลแล้ว.

## 3. เปิด Dashboard project

```bash
cd ~/EDRXDR-Morpheus/frontend || exit 1
npm run start -- --hostname 0.0.0.0 --port 3000
```

เปิด `http://172.16.30.147:3000`; Ctrl+C หยุด. ไม่ต้อง npm install/build ใหม่ถ้า build เดิมใช้ได้.
Audit02:32 ไม่มี port3000 และไม่ได้ทดสอบ HTTP/API. Replay OpenSearch ไม่มี host port;
ห้ามชี้ไป localhost:9200 แล้วคิดว่าเป็น replay (นั่นคือ live OpenSearch).
ก่อนแก้หน้าเว็บให้อ่าน API/config เพื่อยืนยัน endpoint/index จริง และเก็บ credentials ไว้ในเครื่อง.
Wazuh8443 เป็นคนละหน้า. งานค้างคือ Shadow view/API และการแสดง not-scored/weak-label disagreement.

## 4. รอบ Shadow ถัดไป (เฉพาะเมื่อต้องการเก็บข้อมูลเพิ่ม)

Topics/indexes มีแล้ว ไม่ต้อง provision/reset/recreate. Commands ต่อไปเขียน shadow data/group offsets;
รันทีละคำสั่งและตรวจผล. อย่ารัน severity ถ้าไม่มีสิทธิ์ GPU ในเวลานั้น.

```bash
cd ~/EDRXDR-Morpheus || exit 1
docker compose -f shadow/compose.yml run --rm -e SHADOW_RUN_ALLOWED=1 \
  capture capture --limit 32 --seconds 60
docker compose -f shadow/compose.yml run --rm -e SHADOW_RUN_ALLOWED=1 \
  behavioral score --kind behavioral --limit 32 --seconds 15
docker compose -f shadow/compose.yml run --rm -e SHADOW_RUN_ALLOWED=1 \
  indexer index --kind behavioral --limit 32 --seconds 15
```

เมื่อถึงรอบจอง GPU ให้ตรวจ `date` และ `nvidia-smi` ก่อน (GPU ว่างไม่ได้แปลว่ามีสิทธิ์ใช้).
Remote Compose ยังไม่มี cache override ที่ใช้สำเร็จ จึงต้องใส่ครบ:

```bash
docker compose -f shadow/compose.yml run --rm \
  -e SHADOW_RUN_ALLOWED=1 -e SHADOW_GPU_ALLOWED=1 \
  -e HOME=/tmp -e XDG_CACHE_HOME=/tmp/cache \
  -e CUPY_CACHE_DIR=/tmp/cupy-cache -e CUDA_CACHE_PATH=/tmp/cuda-cache \
  severity score --kind severity --limit 32 --seconds 15
docker compose -f shadow/compose.yml run --rm -e SHADOW_RUN_ALLOWED=1 \
  indexer index --kind severity --limit 32 --seconds 15
nvidia-smi
```

งานค้าง: เพิ่มสี่ cache values นี้ใน `x-worker.environment` ของ `shadow/compose.yml`,
ตรวจ config/tests แล้วปรับ package manifest ให้ตรง; docs update นี้ยังไม่แก้ config.
Keep uid1001:gid1002, models read-only, cap_dropALL และ gate ปิดโดย default.
ถ้า permission error ตรวจเฉพาะไฟล์ ห้าม chmod777/chown-R model หรือ repo.

## 5. Acceptance และงานวิจัยที่ยังค้าง

- บันทึก audit/counts/joins ต่อ batch โดย join `event_uid` + source cluster/topic/partition/offset
  พร้อม raw_sha256; UID อย่างเดียวไม่แยก repeated occurrence.
- ต้องมี replay-vs-shadow score parity ของ captured input เดียวกันแยกจาก join test.
- Severity ยังมี weak-label disagreement; Behavioral AE coverage รอบนี้0. เพิ่มข้อมูลและประเมิน
  independent labels ก่อนอ้างตรวจจับภัยจริง. Preserve old-test/reserve ห้ามใช้ tune หลังดูผล.
- ทดสอบ restart duplicate/index acknowledgement failure ด้วย isolated test setup;
  ห้ามหยุด live/shared Kafka/OpenSearch เพื่อสร้าง fault.
- บริการต่อเนื่องต้องออกแบบ rebalance/shutdown, poison-record/dead-letter handling,
  retention/storage monitoring และ GPU schedule. ตอนนี้ใช้ manual bounded workers เท่านั้น.
- ก่อน commit แก้ข้อความเก่าใน shadow/README.md และตรวจ PACKAGE_SHA256 (ไม่ใช่ runtime source-lock).
  ไม่เพิ่ม raw logs, keys, env, caches, datasets หรือ weights เข้า Git.

## 6. ปิดรอบและส่งต่อ

```bash
cd ~/EDRXDR-Morpheus || exit 1
docker ps --filter label=com.docker.compose.project=edrxdr-shadow \
  --format 'table {{.Names}}	{{.Status}}'
git diff --check
git diff --stat
git status --short --untracked-files=all
```

Review แล้วจึง stage/commit ตามการตกลงของทีม; ไม่มีคำสั่ง commit/push อัตโนมัติในชุดนี้.
Backup agent config อยู่ `/var/ossec/etc/ossec.conf.backup-20261011T020813824342`;
agent002 Active หลังแก้ port ตามผลก่อนหน้า ไม่จำเป็นต้อง restart ซ้ำเพื่อสร้าง events.
อย่า stop live containers, prune Docker, down -v, reset offsets หรือเปลี่ยน host GPU/BlueField/DOCA.
ไฟล์ชั่วคราว/สำรองและ Docker volumes อธิบายใน LATEST_STATUS; ตรวจสำเนาก่อน cleanup.

<!-- bluefield-dashboard-verified:start -->
## BlueField Historical Dashboard verification — 2026-10-13T00:52:28+07:00

เพิ่มการแสดงผล BlueField แบบข้อมูลย้อนหลังจาก index
`review-bluefield-20261012t141653z-6396a0d3` โดยไม่เปิด live publisher หรือเปลี่ยน live pipeline

ผลที่ยืนยัน:
- Historical API: PASS
- Dashboard UI: PASS
- Historical records: 6
- Interfaces: 2
- carrier null/Unknown: 6
- first-sample delta null/N/A: 2
- computed delta zero: 4
- BlueField synthetic tests: 7 PASS
- TypeScript typecheck: PASS
- Frontend regression: 7 groups PASS
- Next.js production build: PASS
- `null` และ `0` รักษาความหมายแยกกัน
- API ระบุ `mode=historical_review`
- API ระบุ `live=false`
- API ระบุ `production_ready=false`

BlueField service หลังทดสอบ:
- ActiveState=inactive
- SubState=dead
- UnitFileState=disabled

Safety:
- ไม่ start/enable `edrxdr-bluefield.service`
- ไม่ส่ง schema ทดลองเข้า live Kafka topic
- ไม่เปลี่ยน driver/interface
- ไม่ใช้ GPU
- ไม่เปิด automated response
- ข้อมูลนี้เป็น historical review ไม่ใช่ live telemetry หรือ production-readiness evidence

หลักฐาน:
- `training/evidence/bluefield-dashboard-20261012/api-verification.json`
- `training/evidence/bluefield-dashboard-20261012/service-state.txt`
- `training/evidence/bluefield-dashboard-20261012/ui-verification.txt`
- `experiments/bluefield-opensearch-runs/20261012T141653Z-6396a0d3/report.json`
- `experiments/bluefield-kafka-runs/20261012T141233Z-beaccd98dc/report.json`

งานถัดไป:
- review/stage หลักฐานและ source แบบ explicit
- ห้ามใช้ `git add .`
- ยังไม่เปิด BlueField live service
- งาน live/continuous consumer และ production validation ยังไม่ทำ
<!-- bluefield-dashboard-verified:end -->

<!-- bluefield-shadow-v1:start -->
## BlueField Shadow v1 — bounded archived pilot

Last verified: `2026-10-13T01:46:35+07:00`

Git at verification:
- Branch: `work/bluefield-shadow-v1`
- Base HEAD before this checkpoint commit: `6940d49ba29c`

Status: **PASS for bounded/manual archived Shadow evaluation only.**
This is **not** live BlueField telemetry and is **not production-ready**.

Verified data flow:

```text
committed archived BlueField normalized evidence
  -> replay Kafka: shadow-bluefield-input-v1
  -> bounded/manual validator + indexer
  -> replay OpenSearch: shadow-bluefield-v1
  -> /api/shadow/bluefield
  -> /shadow : BlueField Shadow Evidence
```

Verified runtime state:
- Kafka input records: **6**
- Consumer group: `edrxdr-shadow-bluefield-index-v1`
- Consumer offset: **6 / 6**
- Consumer lag: **0**
- OpenSearch index: `shadow-bluefield-v1`
- Indexed documents: **6**
- API mode: `shadow_bluefield`
- `historical=true`
- `live=false`
- `production_ready=false`
- `automated_response_allowed=false`
- Interfaces: **2**
- Carrier null/Unknown: **6**
- RX counter zero preserved: **6**
- First-sample delta null/N/A: **2**
- Computed delta zero preserved: **4**

Verification completed in this work session:
- `python3 -B shadow/test_bluefield_shadow.py`: **8/8 PASS**
- `frontend/tests/bluefield-shadow.cjs`: **10 checks PASS**
- existing `frontend/tests/shadow.cjs`: **20 checks PASS**
- TypeScript `tsc --noEmit`: **PASS**
- frontend regression: **7 groups PASS**
- ESLint: **0 errors**; one pre-existing warning in `tests/bluefield-history.cjs`
- Next.js production build: **PASS**
- manual `/shadow` UI verification: **PASS**

Safety state after testing:
- `edrxdr-bluefield.service`: **inactive / dead / disabled**
- No live `bluefield-events` topic was used by this pilot.
- No network driver/interface changes.
- No GPU use.
- No automated response.
- `raw_event` and literal `capture_scope` are not exposed through the Shadow browser projection.

Evidence:
- `training/evidence/bluefield-shadow-20261012/api.json`
- `training/evidence/bluefield-shadow-20261012/service-state.txt`
- `training/evidence/bluefield-shadow-20261012/ui-verification.txt`
- `shadow/BLUEFIELD_SHADOW.md`

Important limitations / remaining work:
- The pilot uses committed archived normalized evidence, not live sampling.
- Workers are finite one-shot/manual jobs, not a continuous consumer service.
- Long-term retention, poison-message handling, restart/recovery policy, continuous sampling, production capacity and production security review remain pending.
- Do not enable `edrxdr-bluefield.service` or connect experimental BlueField schema to shared/live topics without a separate review.
<!-- bluefield-shadow-v1:end -->

<!-- bluefield-shadow-recovery:start -->
## BlueField Shadow isolated recovery/resume verification

Last verified: `2026-10-13T02:06:56+07:00`

Git at verification:
- Branch: `work/bluefield-shadow-recovery`
- Base HEAD before this checkpoint commit: `cc4b43918dcb`

Status: **PASS for isolated bounded recovery/resume testing only.**

Recovery sequence verified:
- Phase 1: start offset **0**, processed **3**, committed offset **3**, lag **3**, docs **3**
- Fresh container Phase 2: start offset **3**, processed **3**, committed offset **6**, lag **0**, docs **6**
- Rerun: start offset **6**, processed **0**, committed offset **6**, lag **0**, docs **6**
- Final verification: **6 unique documents**, no duplicates

Semantics preserved:
- Carrier null/Unknown: **6**
- RX counter zero: **6**
- First-sample delta null/N/A: **2**
- Computed delta zero: **4**
- `historical=true`
- `live=false`
- `production_ready=false`
- `automated_response_allowed=false`

Isolation/safety:
- Recovery test used dedicated Kafka topic, consumer group and OpenSearch index.
- Main `shadow-bluefield-input-v1` remained at offset **6/6**, lag **0**.
- Main `shadow-bluefield-v1` remained at **6 documents**.
- `edrxdr-bluefield.service` remained **inactive / dead / disabled**.
- No `bluefield-events` use, no live sampling, no GPU, no network driver/interface changes, no automated response.

Evidence:
- `training/evidence/bluefield-shadow-recovery-20261012/run-id.txt`
- `training/evidence/bluefield-shadow-recovery-20261012/context.txt`
- `training/evidence/bluefield-shadow-recovery-20261012/recovery-result.txt`
- `training/evidence/bluefield-shadow-recovery-20261012/consumer-group.txt`
- `training/evidence/bluefield-shadow-recovery-20261012/index.txt`
- `training/evidence/bluefield-shadow-recovery-20261012/service-state.txt`
- `training/evidence/bluefield-shadow-recovery-20261012/final-verify.txt`

Remaining work:
- This does not prove continuous/live BlueField operation.
- Long-running consumer supervision, poison-message policy, retention policy, production capacity, production security review and live capture remain pending.
- Do not enable `edrxdr-bluefield.service` or connect experimental BlueField schema to shared/live topics without separate review.
<!-- bluefield-shadow-recovery:end -->

<!-- bluefield-shadow-failure-tests:start -->
## BlueField Shadow fail-closed commit-boundary verification

Last verified: `2026-10-13T02:23:40+07:00`

Git at verification:
- Branch: `work/bluefield-shadow-failure-tests`
- Base HEAD before this checkpoint commit: `018834ad0c84`

Status: **PASS for isolated failure-injection testing only.**

Poison-message scenario:
- valid source offset 0 indexed successfully
- Kafka committed offset advanced to **1**
- source offset 1 contained a strict-schema-invalid BlueField record
- validation rejected the poison record
- committed offset remained **1**
- log end offset remained **3**
- lag remained **2**
- isolated index remained at **1 document**
- a fresh process retried the same source offset **1**
- the later valid record at offset 2 was **not silently skipped**

OpenSearch failure-before-commit scenario:
- valid source offset 0 passed BlueField validation
- isolated OpenSearch strict mapping rejected the write
- Kafka committed offset remained **unset**
- isolated index remained at **0 documents**
- the isolated index was repaired without restarting/reconfiguring shared OpenSearch
- a fresh process retried the same source offset **0**
- after OpenSearch ACK, Kafka committed offset **1**
- final lag **0**
- final isolated docs **1**

Recovered-document semantics:
- carrier null/Unknown preserved
- counter zero preserved
- first-sample delta null preserved
- `historical=true`
- `live=false`
- `production_ready=false`
- `automated_response_allowed=false`

Main-pipeline safety after cleanup:
- main `shadow-bluefield-input-v1`: offset **6/6**, lag **0**
- main `shadow-bluefield-v1`: **6 documents**
- `edrxdr-bluefield.service`: **inactive / dead / disabled**
- no live `bluefield-events` use
- no GPU use
- no network driver/interface changes
- no automated response

Evidence:
- `training/evidence/bluefield-shadow-failure-20261012/run-id.txt`
- `training/evidence/bluefield-shadow-failure-20261012/context.txt`
- `training/evidence/bluefield-shadow-failure-20261012/poison-verify.txt`
- `training/evidence/bluefield-shadow-failure-20261012/osfail-verify.txt`
- `training/evidence/bluefield-shadow-failure-20261012/poison-group.txt`
- `training/evidence/bluefield-shadow-failure-20261012/osfail-group.txt`
- `training/evidence/bluefield-shadow-failure-20261012/indices.txt`
- `training/evidence/bluefield-shadow-failure-20261012/service-state.txt`
- `training/evidence/bluefield-shadow-failure-20261012/result.txt`
- `shadow/BLUEFIELD_FAILURE_TESTS.md`

Remaining work:
- A production poison-message policy (DLQ/quarantine/operator workflow) is not implemented.
- Long-running consumer supervision, retry/backoff policy, retention policy, capacity testing, production security review and live capture remain pending.
- Do not enable `edrxdr-bluefield.service` or connect experimental BlueField schema to shared/live topics without separate review.
<!-- bluefield-shadow-failure-tests:end -->

<!-- bluefield-shadow-quarantine:start -->
## BlueField Shadow Quarantine v1 verification

Last verified: `2026-10-13T02:40:37+07:00`

Git at verification:
- Branch: `work/bluefield-shadow-quarantine`
- Base HEAD before this checkpoint commit: `469147182e3c`

Status: **PASS for isolated bounded quarantine/DLQ policy testing only.**

Verified source flow:
- input record 0: valid -> valid index ACK -> source commit to offset **1**
- input record 1: poison -> strict validation failure
- first quarantine attempt: quarantine index rejection -> source offset remained **1**
- after isolated quarantine-index repair, fresh process retried source offset **1**
- quarantine index ACK + quarantine Kafka ACK completed before source commit
- source committed to offset **2**
- input record 2: valid -> indexed -> source committed to offset **3**

Final isolated state before cleanup:
- input records: **3**
- committed offset: **3 / 3**
- lag: **0**
- valid documents: **2**
- valid source offsets: **0, 2**
- quarantine documents: **1**
- quarantine Kafka records: **1**
- quarantine source offset: **1**
- raw poison payload stored: **false**

Quarantine envelope safety:
- stores source topic / partition / offset
- stores SHA-256 of source input
- stores reason code, error class, validation stage and quarantine timestamp
- does **not** store raw input body
- does **not** expose `raw_event` or literal `capture_scope`
- `historical=true`
- `live=false`
- `production_ready=false`
- `automated_response_allowed=false`

Failure boundary verified:
- if quarantine storage fails, source Kafka offset does **not** advance
- no quarantine Kafka record is emitted on the failed quarantine attempt
- a fresh process retries the same poison source offset after repair
- source offset advances only after both quarantine sinks acknowledge the record

Main-pipeline state after isolated-resource cleanup:
- main `shadow-bluefield-input-v1`: offset **6 / 6**
- main lag: **0**
- main `shadow-bluefield-v1`: **6 documents**
- `edrxdr-bluefield.service`: **inactive / dead / disabled**
- no live `bluefield-events` use
- no GPU use
- no network driver/interface changes
- no automated response

Evidence:
- `training/evidence/bluefield-shadow-quarantine-20261012/run-id.txt`
- `training/evidence/bluefield-shadow-quarantine-20261012/context.txt`
- `training/evidence/bluefield-shadow-quarantine-20261012/consumer-group.txt`
- `training/evidence/bluefield-shadow-quarantine-20261012/indices.txt`
- `training/evidence/bluefield-shadow-quarantine-20261012/service-state.txt`
- `training/evidence/bluefield-shadow-quarantine-20261012/final-verify.txt`
- `training/evidence/bluefield-shadow-quarantine-20261012/result.txt`
- `shadow/BLUEFIELD_QUARANTINE.md`

Remaining work:
- Quarantine/DLQ is still an isolated test policy, not a continuous production service.
- Operator review/replay tooling for quarantined records is not implemented.
- Retry/backoff policy, retention policy, alerting, long-running supervision, capacity testing, production security review and live capture remain pending.
- Do not enable `edrxdr-bluefield.service` or connect experimental BlueField schema to shared/live topics without separate review.
<!-- bluefield-shadow-quarantine:end -->
