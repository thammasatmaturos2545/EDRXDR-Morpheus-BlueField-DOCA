# Source review update — 11 ต.ค. 2026 (ยังไม่ใช่การรันใหม่บน VM)

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

# Latest status — verified Shadow pilot

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


## ขอบเขตหลักฐาน

Audit: `/tmp/edrxdr-handoff-audit-g7HuGkxo.tar.gz` จาก VM;
สำเนา Windows `C:\Users\bagel\Downloads\edrxdr-handoff-audit-g7HuGkxo.tar.gz`.
หลักฐานที่แนบใน repo: [evidence/shadow-20261011](evidence/shadow-20261011/).
ตรวจ source-lock ทั้ง 12 ไฟล์จาก snapshot ตรงกับ SHA-256 ที่กำหนด.
Audit ไม่ได้ rerun training, GPU parity, frontend build, secret scan หรือทดสอบ outage.

## ผลที่ตรวจล่าสุด

| Check | ผล | หลักฐาน |
|---|---|---|
| CPU Shadow contracts | 23 tests PASS | `evidence/shadow-20261011/shadow-tests.txt` |
| Compose syntax/config | PASS | `compose-check.txt` ใน evidence |
| Git diff check ก่อนแก้เอกสาร | ไม่มี error; tracked tree เดิมไม่เปลี่ยน | `git.txt`; ไม่ครอบคลุม untracked shadow |
| Severity index | 32, failed shards 0 | `shadow-severity-count.json` |
| Behavioral index | 32, failed shards 0 | `shadow-behavioral-count.json` |
| Occurrence join / raw hash | PASS 32/32 | `join-evidence.txt` |
| Shadow consumers สี่กลุ่ม | offset 32/end 32/lag 0; inactive หลังจบ | `replay-groups.txt` |
| Live normalizer/indexer | lag 0 ณ audit | `live-groups.txt`; ไม่ใช่หลักฐานไม่มีผลกระทบตลอดเวลา |
| Container/listeners | ไม่มี Shadow worker; ไม่มี port 3000 | `containers.txt`, `listeners.txt` |

รายงานต้นฉบับ: volume `edrxdr-shadow_shadow-state`,
`/join-check-20261010T192035112516Z.json` (ใน worker คือ `/shadow-state/...`).
Evidence hash `41ea206d7f5c61df958634bfab041cc5bf1b15b51f4a0759c43f3b0cd21d9a2e`.
รายงานยืนยัน output contracts/occurrence join เท่านั้น ไม่ใช่ accuracy หรือ replay-vs-shadow score parity.

ผล terminal รอบ pilot ก่อน audit: capture 32, severity 32 (~7.016 s รวมงานใน batch),
behavioral 32 (~1.016 s), index อย่างละ 32. Severity false-positive candidates 13.
Behavioral: limited_history 31, novel_cohort 1; ae_scored 0, novelty 1.
Capture-to-score รวมเวลารอคำสั่งคน จึงไม่ใช่ latency SLA.
GPU 02:20:46 ไม่มี process/ใช้ 0 MiB ตาม nvidia-smi ที่ผู้ใช้ส่ง; audit ไม่ได้รัน nvidia-smi ซ้ำ.

## Kafka offsets

Capture อ่าน live `wazuh-alerts` partition 0 เริ่ม 15573 → commit 15605 = 32 events.
Audit ล่าสุด end 15854, lag **249** (เพิ่มจาก 246 ที่ตรวจครั้งก่อน) เป็น backlog ที่ตั้งใจยังไม่คัดลอก.
ไม่ reset offsets. Resume ได้เฉพาะเมื่อข้อมูลยังอยู่ใน retention; code จะหยุดเมื่อ offset หมดอายุ.
กลุ่มเก่า `replay-behavioral-archive-v1` lag 7 และ `replay-behavioral-v1` lag 8 ให้คงไว้.
`edrxdr-dataset-1791376700` inactive lag 15552 ไม่ใช่งาน Shadow.

## Git

Base HEAD `12d6049741235ba4bb45d65c1e3f59d4e01ce5b3` (`Refresh project handoff documentation`).
ก่อนติดตั้ง docs ใหม่มี untracked 11 ไฟล์:

```text
shadow/LOCAL_TEST_REPORT.json
shadow/PACKAGE_SHA256.json
shadow/README.md
shadow/common.py
shadow/compose.yml
shadow/pilot.py
shadow/runtime.py
shadow/scoring.py
shadow/source-lock.json
shadow/test_shadow.py
shadow/validation.py
```

หลังติดตั้งชุดนี้จะมี README.md, training/LATEST_STATUS.md, training/HANDOFF.md เปลี่ยน
และ `training/evidence/shadow-20261011/` เพิ่ม; ชุดนี้ไม่แก้ runtime หรือ commit/push.
`shadow/README.md` เดิมยังมีสถานะเก่า; ใช้เอกสารสามไฟล์นี้เป็นสถานะล่าสุด และแก้ README ย่อยก่อนส่งต่อ release.

## Dataset/model/storage

| Docker volume | ตำแหน่งภายใน volume / การใช้งาน |
|---|---|
| edrxdr-dataset | `/wazuh-history-20261008T184838Z-1179365` snapshot Wazuh history |
| edrxdr-dataset | `/wazuh-context-v2-20261008T185539Z-1179365` dataset v2 / manifest |
| edrxdr-model-output | `/wazuh-severity-context-v2-balanced-20261008T190719Z-1398863` checkpoint ที่ Shadow ใช้จริง |
| edrxdr-model-output | `/morpheus-behavioral-v1-4-dev` runtime, manifest และ cohort models |
| edrxdr-model-output | `/morpheus-raw-offline-check-20261008T203523Z-1803526/parity_report.json` parity ที่ severity ตรวจ hash ก่อนใช้ |
| edrxdr-model-output | `/morpheus-offline-check-20261008T194814Z-1588236/parity_report.json` ผล offline เดิม |
| edrxdr-hf-cache | Hugging Face cache; ไม่ใช่ final model |
| edrxdr-shadow_shadow-state | audit.jsonl, role locks, join report; ไม่ลบเพื่อเริ่มรอบใหม่ |

Mountpoints ยืนยันโดย `volume-paths.txt`: `/docker/volumes/<volume>/_data` สำหรับ dataset,
model-output และ shadow-state. อ่านผ่าน container mount แบบ read-only แทนแก้ host Docker storage.
Shadow mounts models เป็น `/models` และ state เป็น `/shadow-state`.
Dataset v2 เดิม: train 5232 / validation 1314 / quarantine_old_test 1398 / reserve_new_rules 479;
จำนวนเหล่านี้มาจากการเตรียมข้อมูลก่อนหน้า ไม่ได้นับซ้ำใน audit นี้.
รายการ artifact/report ทั้งหมดอยู่ใน `edrxdr-model-output-files.txt` และ `edrxdr-dataset-files.txt` ใน evidence.
มี historical smoke/failed parity directories ด้วย: การมีไฟล์ report ไม่ได้แปลว่ารายนั้น PASS.

## Running containers ณ audit

```text
NAMES                        STATUS                  IMAGE                                            PORTS
edrxdr-replay-opensearch-1   Up 45 hours             opensearchproject/opensearch:2.11.0              9200/tcp, 9300/tcp, 9600/tcp, 9650/tcp
edrxdr-replay-normalizer-1   Up 45 hours             edrxdr-morpheus-normalizer:latest
edrxdr-replay-kafka-1        Up 45 hours             apache/kafka:3.8.1                               9092/tcp
edrxdr-morpheus              Exited (1) 8 days ago   nvcr.io/nvidia/morpheus/morpheus:25.06-runtime
edrxdr-normalizer            Up 3 days               edrxdr-morpheus-normalizer
edrxdr-wazuh-forwarder       Up 3 days               wazuh-wazuh.forwarder
wazuh-wazuh.dashboard-1      Up 3 days               wazuh/wazuh-dashboard:4.14.7                     443/tcp, 0.0.0.0:8443->5601/tcp, [::]:8443->5601/tcp
wazuh-wazuh.indexer-1        Up 3 days               wazuh/wazuh-indexer:4.14.7                       0.0.0.0:9201->9200/tcp, [::]:9201->9200/tcp
wazuh-wazuh.manager-1        Up 3 days               wazuh/wazuh-manager:4.14.7                       0.0.0.0:1514-1515->1514-1515/tcp, [::]:1514-1515->1514-1515/tcp, 0.0.0.0:514->514/udp, [::]:514->514/udp, 0.0.0.0:55000->55000/tcp, [::]:55000->55000/tcp, 1516/tcp
edrxdr-indexer               Up 3 days               edrxdr-morpheus-indexer
edrxdr-kafka                 Up 3 days               apache/kafka:3.8.1                               0.0.0.0:9092->9092/tcp, [::]:9092->9092/tcp
edrxdr-opensearch            Up 3 days               opensearchproject/opensearch:2.11.0              9300/tcp, 9600/tcp, 0.0.0.0:9200->9200/tcp, [::]:9200->9200/tcp, 9650/tcp
```

`edrxdr-morpheus` เดิม Exited (1) ไม่ใช่ Shadow worker. ไม่มีคำสั่ง restart บริการเดิมในชุดเอกสารนี้.
Replay OpenSearch ไม่มี host port; รัน read-only queries ผ่าน `docker exec` หรือ network replay.
Dashboard project ไม่ได้ฟัง 3000 ณ audit; frontend source/API ไม่ได้รวมทั้งหมดใน snapshot
จึงไม่ยืนยันว่า UI แสดง Shadow แล้ว.

## ปัญหาที่แก้แล้ว / ข้อจำกัด

- VM worker ใช้ UID 1001:GID 1002 ให้อ่าน training directory mode 700 ได้;
  shadow-state root ถูก chown เฉพาะ directory. ไม่ทำ recursive chmod/chown ทั้ง repo.
- Checkpoint weights เดิม root:root 600 ถูกแก้เฉพาะไฟล์เป็น root:1002 640 ตามผลรอบก่อน;
  hash ก่อน/หลังตรงกัน. Audit นี้ไม่ได้ตรวจ permission ซ้ำ.
- Model image ไม่มี kafka-python ที่ validator เดิม import: Shadow SHA-check แล้ว AST-load เฉพาะ
  pure validation functions; tests ตรวจกรณีไม่มี Kafka import. ไม่ติดตั้ง dependency เพิ่ม.
- Live/replay brokers มี cluster ID เดียวกัน; guard ตรวจ advertised endpoint + topic signatures
  ร่วมกัน. ไม่ reformat broker/storage. Guard ไม่ใช่ ACL/security boundary.
- Severity รันสำเร็จเมื่อกำหนด HOME/XDG/CUPY/CUDA caches เป็น /tmp; **remote Compose ยังไม่มีสี่ค่านี้**.
- Membind warning ไม่ทำให้ batch ล้ม; ไม่ต้องเพิ่ม SYS_NICE เพื่อปิด warning.
- Host Wazuh agent 002 เดิมต่อ localhost:1516; แก้เป็น 127.0.0.1:1514 แล้ว restart เฉพาะ agent
  ตามที่อนุญาต. Active และ Kafka มี events ใหม่; ไม่ restart manager หรือ host.
- Model quality ยังมี weak-label disagreement และ unseen-rule weakness; ไม่มี independent attack truth.
- Shadow topics ตั้ง retention 24h/64 MiB ต่อ partition ตอนสร้าง; index retention ยัง manual.
- Unit tests ครอบคลุม retry/ack ordering แบบจำลอง ไม่ใช่ outage/restart test กับบริการจริง.
- ยังไม่มี scoring parity ของ replay เทียบ Shadow สำหรับ captured batch นี้ และยังไม่มี sustained service.

## หลักฐานเดิม (ไม่ rerun รอบนี้)

ผล temporal-v1, Replay 8/8 joins, Next.js build และ parity เดิมเก็บใน
[previous-status-20261010.md](evidence/shadow-20261011/previous-status-20261010.md).
เอกสารนั้นเป็น historical snapshot ไม่ใช่สถานะปัจจุบัน. Temporal dev-unseen N=19 มี FN16,
recall0 ทั้ง balanced/unweighted ตามรายงานเดิม; ห้ามใช้ seen-rule score อ้างเป็นความแม่นยำ threat detection.
ตำแหน่งรายงานเดิม `training/experiments/temporal-v1/{dataset-manifest,balanced-report,unweighted-report}.json`
อ้างจาก handoff ก่อนหน้า ไม่ได้รวบรวมเนื้อหาไฟล์เหล่านั้นใน audit นี้.

## ไฟล์นอก repo

Inventory จริง: [outside-repo.txt](evidence/shadow-20261011/outside-repo.txt).
สคริปต์ inventory พิมพ์ basename ของ home แล้ว /tmp ต่อกัน จึงไม่ยืนยัน absolute path ของทุกชื่อ.
รายการต่อไปแยกหน้าที่ที่ทราบจากรอบงานออกจากรายการที่ยังไม่ได้ตรวจเนื้อหา:

| ไฟล์/กลุ่ม | หน้าที่ / สิ่งที่ยังไม่ยืนยัน |
|---|---|
| /tmp/edrxdr-handoff-audit-g7HuGkxo* | snapshot audit และ archive ที่ใช้เขียนเอกสารนี้ |
| /tmp/collect_handoff_audit.sh | ตัวเก็บหลักฐานล่าสุด; ไม่ใช่ runtime |
| /tmp/edrxdr-shadow-source-12d6049.tar.gz | source snapshot ฐานงาน Shadow |
| /tmp/edrxdr-shadow-pilot-12d6049-20261011.tar.gz | แพ็กเริ่มต้น; ต้องมี routing/validator fixes จึงเป็นรุ่นล่าสุด |
| /tmp/edrxdr-shadow-routing-fix-20261011.tar.gz | patch guard กรณี broker ID ซ้ำ |
| /tmp/edrxdr-shadow-validator-fix-20261011.tar.gz | patch validator ไม่พึ่ง kafka-python |
| /tmp/shadow-before-routing-fix-* และ shadow-before-validator-fix-* | backup ก่อน patch; ไม่ใช่ตัวรันปัจจุบัน |
| /tmp/multireplay-*.log, replay-api-joined-3101.json | log/response ของ replay เดิมตาม handoff; มีอยู่ แต่ไม่ได้อ่านเนื้อหาซ้ำ |
| /tmp/edrxdr-temporal-v1*, edrxdr-anomaly-v1* | dataset/run artifacts ของการทดลองเดิมตาม handoff; เก็บจนตรวจว่ามีสำเนาแล้ว |
| ~/edrxdr-dashboard-review-*, edrxdr-dashboard-updated.zip, edrxdr-frontend-backup-*, edrxdr-before-dashboard-* | ชื่อบ่งชี้ staging/update/backup dashboard; ยังไม่ได้ตรวจเนื้อหาและห้ามใช้แทน repo โดยอัตโนมัติ |
| ~/EDRXDR-Morpheus-personal, ~/EDRXDR-HANDOFF | checkout/ชุดส่งต่ออีกตำแหน่ง; ยังไม่ตรวจ branch หรือความใหม่ อย่าแก้แทน repo หลัก |
| ~/venvs, ~/wazuh-agent_4.14.1-1_amd64.deb | environment directory / installer package; ไม่ใช่ model checkpoint |
| edrxdr-exp1-seed-*, edrxdr-v3-exp1*, edrxdr-behavioral-*, dashboard archives/scripts อื่นใน inventory | พบชื่อเท่านั้น ยังไม่ยืนยันเนื้อหา/บทบาทล่าสุด |
| /var/ossec/etc/ossec.conf.backup-20261011T020813824342 | backup host-agent ก่อนแก้ port ตาม terminal ก่อนหน้า; อย่าเผยแพร่ config/credentials |

ไฟล์ /tmp อาจหายหลัง cleanup/reboot. ห้ามลบหรืออ้างว่าเป็นของกลุ่มเราทั้งหมดจากชื่อ/วันที่เพียงอย่างเดียว.
ไม่มี raw events, passwords, .env หรือ model weights ใน evidence ที่แนบชุดนี้.

## งานถัดไป

ทำตาม [HANDOFF.md](HANDOFF.md): review docs/Git, persist cache settings,
ตรวจ UI/API และ Shadow display, ประเมิน coverage/คุณภาพ, ทดสอบ parity/recovery แบบ isolated.
ไม่ train ใหม่หรือเปิด daemon เพียงเพื่อให้หน้า Dashboard มีข้อมูล.

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
