# ส่งต่องาน EDRXDR-Morpheus / NEXUS — 20 ตุลาคม 2026

เอกสารนี้สรุปจากผลคำสั่งที่ผู้ดูแล VM รายงานใน session นี้ ไม่ใช่การตรวจ runtime ใหม่ ข้อมูลจริงและ secret ต้องอยู่บน VM ตามสิทธิ์ที่ได้รับ

## จุดเริ่มต้น

- VM: `saiuser@172.16.30.147`
- Repo: `/home/saiuser/EDRXDR-Morpheus`
- Branch: `work/nexus-exact-ai-v1`
- HEAD ก่อนเพิ่มเอกสารนี้: `01b6088fd4a66eddb256ea1787167d5d67b803d1`
- Node ที่ใช้ตรวจ: `/home/saiuser/.nvm/versions/node/v20.20.2/bin/node`
- ไฟล์รับเข้าใหม่ให้ใช้ `/mnt/nexus-copilot-mQTssj/incoming/` ไม่วางใน home หรือ `/tmp`
- ยังมี WIP/untracked นอกชุดที่ commit แล้ว ต้องตรวจและรักษาไว้ ห้าม `reset`, `clean`, `checkout` หรือเขียนทับ

## สิ่งที่ทำแล้ว

| Commit | ขอบเขต |
| --- | --- |
| `af6d8d1` | SOC summary mock ใช้ synthetic evidence และ auth |
| `6922c4a` | หน้า saved Copilot review พร้อม authenticated API |
| `16d5422` | จำกัด Wazuh source ตาม compose project/service และตรวจ container ID |
| `f8e4e5a` | Exact UID Lookup + ตรวจ canonical source; จำกัด response ขณะอ่าน |
| `b13dd7e` | Copilot evidence adapter + complete AI reader |
| `b10cfec` | Endpoint inventory จากเครื่องที่พบใน Wazuh rows |
| `c0f793c` | อ่านท้ายไฟล์ไม่เกิน 4 MiB แล้วเลือกไม่เกิน 100 alerts |
| `6e9cd36` | History auth/query validation + complete AI safeguards |
| `01b6088` | รวม All Events/Research ใน Dashboard และแก้การแสดงสถานะ/เวลาที่ไม่ทราบ |

ชุดสุดท้ายตรวจทั้ง 3 cumulative stages ในพื้นที่แยกผ่านก่อนสร้าง 3 commit: sampling, History, Dashboard รวม tests ที่เกี่ยวข้อง, TypeScript และ whitespace diff พร้อมตรวจ Git bundles หลัง commit โดยรายงานว่า normal index สะอาดและรักษา WIP นอกชุดไว้

**ไม่มี push, deploy, production build หรือ restart service ในชุดนี้** การ commit ไม่ได้ยืนยันว่า runtime 3001/3006 ใช้โค้ดล่าสุด

## พฤติกรรมและข้อจำกัด

- Wazuh resolver ต้องมี `WAZUH_COMPOSE_PROJECT` ที่ตรวจแล้ว; ไม่พบ/พบหลาย container/identity ผิดต้อง fail closed ห้าม fallback ไป project ทีมอื่น
- Exact UID ตรวจ reference index/document ID และคำนวณ canonical UID จาก source ใหม่ ไม่อนุมาน match จากเวลา/host
- Copilot แยก `matched`, `not_scored`, `conflict`, `unavailable`; คะแนน `0` ต่างจาก `null` และไม่ใช่ความน่าจะเป็นการโจมตี
- AI reader ตรวจ model/provenance, exact keyword query, counts/shards/timeout และปริมาณข้อมูล การอ่านไม่ครบไม่ถือว่าไม่มีคะแนน
- History ใช้ complete reader เป็น batch ไม่เกิน 8 UID พร้อม page deadline; batch ใดล้มเหลวให้ AI ทั้งหน้า unavailable
- History ยังพึ่ง external script `/home/saiuser/nexus-history-preview-20261020/query_history.py` และ SQLite snapshot เดิม ซึ่งยังไม่ถูกบรรจุเป็น deployment ที่ย้ายเครื่องได้ในชุดนี้
- History/Copilot auth ใช้ implementation ใน `frontend/src/lib/history-auth.ts`; ห้ามคัดลอก secret ลงเอกสาร/แชต/command line หรือเปิด auth ออก
- Endpoint เป็น observed inventory จาก rows ที่โหลดมา ไม่ใช่ inventory ครบระบบ; ปัจจุบันรับ Agent ID 3 หลัก ยกเว้น `000`; health/risk/time ที่ไม่ทราบต้องคง unknown/null
- Sampling ไม่เกิน 100 rows จากช่วงท้าย 4 MiB ไม่ใช่ ingestion total หรือความครอบคลุมทุกเครื่อง และไม่มี strict per-agent cap หลังขั้นเติมข้อมูล
- Research/BlueField views เป็น historical review ไม่ได้เปิด live service
- Copilot ปัจจุบันเป็นการแสดง saved review; ยังไม่มี live Analyze workflow ที่ประเมินพร้อมใช้งานจริง

## การประเมิน LLM

- ใช้โมเดลสำเร็จรูป `gpt-oss-20b` บนเครื่องภายใน ไม่มี training และไม่ส่ง raw logs ไป external provider
- Model revision: `6cee5e81ee83917806bbde320786a8fb61efebee`
- ผู้ดูแลรายงาน exact source และ evidence/AI matched 8/8 UID; สร้างสรุปได้ 8/8 และ integrity ของ evidence/score/citations ผ่าน 8/8
- สิ่งนี้ไม่ได้รับรอง semantic accuracy หรือว่าเป็น 8 incidents อิสระ ทั้งหมดยังต้อง Analyst review; Event 1 เคยถูกระบุ `needs_revision` โดยต้นฉบับยังคงเดิม
- สิทธิ์ GPU ของ session นี้สิ้นสุด 20 ต.ค. 2026 เวลา 12:00 ICT; launcher ตั้งหยุด 11:55 แต่ไม่มีผลตรวจ GPU release ล่าสุดใน handoff นี้
- ห้ามเริ่ม inference/training/GPU ใหม่ก่อนยืนยัน reservation ใหม่ แม้ GPU ว่าง

## ข้อห้ามบน shared VM

- ห้ามแก้ driver/network หรือหยุด shared stack; ห้ามแตะระบบทีมอื่น
- ติดตั้ง dependency เฉพาะ venv/พื้นที่แยก ไม่แก้ system Python/CUDA/driver
- ห้าม build ทับ `.next` ของ runtime, restart service หรือเปลี่ยน shared systemd state โดยพลการ
- BlueField/rshim ต้อง inactive/dead/disabled และ automated response ต้อง OFF; สถานะที่เคยรายงานเป็นเช่นนั้น ต้องตรวจปัจจุบันอีกครั้ง
- ห้ามทำ automated response หรือเปลี่ยน Morpheus severity/AI scores จากผลสรุป LLM

## งานถัดไปตามลำดับ

1. ตรวจ branch/HEAD, Git WIP, handoff และ current service/process metadata แบบ read-only ก่อนทำงาน
2. ยืนยันว่า LLM process เดิมหยุดและ GPU คืนแล้ว; ไม่เริ่ม GPU ใหม่จนมี reservation
3. เตรียม candidate แยกจาก runtime แล้วตรวจ History script/database/auth/source config และ UI ด้วยข้อมูลที่ได้รับอนุญาต ห้ามนำ secret/raw evidence ออก
4. ทำ Analyst semantic review ให้ครบชุด 8 UID และบันทึกเหตุผลแยกจาก model output ต้นฉบับ
5. ประเมิน dedicated read-only OpenSearch credential, authorization ของ API ที่เหลือ, rate limits, retention/restore และ packaging ของ History dependency
6. ตรวจและจัดชุด WIP ที่ยังเหลือ เช่น `history/`, `uid_lookup/`, historical evidence/handoffs อย่า `git add .`
7. เสนอ candidate validation + deployment/rollback plan ที่ตรวจแล้วก่อน deploy; ยังไม่ควรถือว่าพร้อม production

## ตรวจเริ่มงานบน VM (read-only)

```bash
cd /home/saiuser/EDRXDR-Morpheus || exit 1
git branch --show-current
git log -5 --oneline
git status --short
git --no-pager diff --check
systemctl --user show nexus-all-events-prod-3001.service nexus-all-events-prod-3006.service \
  --no-pager -p Id -p ActiveState -p MainPID
systemctl show edrxdr-bluefield.service rshim.service \
  --no-pager -p Id -p ActiveState -p SubState -p UnitFileState
```

อย่า dump `Environment`, secret files, raw logs หรือ full private evaluation report เพื่อส่งต่อ ใช้สิทธิ์บน VM และสรุปผลเท่าที่จำเป็น

## การจัดเก็บและความเป็นส่วนตัว

- ย้าย transfer archives 8 ไฟล์จาก `/tmp` เข้าพื้นที่ session ส่วนตัวแบบกู้คืนได้แล้ว
- ย้าย old test folders 35 แห่งเข้า `~/.edrxdr-private/old-tests-mvbpfcd4/`; manifest `moves.jsonl`; อีก 27 แห่งถูกข้าม ไม่ลบถาวร
- เก็บ repo/runtime/preview/หลักฐานสำคัญไว้ตำแหน่งเดิม Git HEAD/WIP ไม่เปลี่ยนจากการจัดเก็บ
- พื้นที่ session `/mnt/nexus-copilot-mQTssj` และ archive ส่วนตัวใช้สิทธิ์ `700`; ไม่ป้องกันผู้ที่ใช้บัญชี `saiuser` เดียวกัน ต้องแยกบัญชีหากต้องการแยกสิทธิ์บุคคล
- Bundles/checkpoints เป็นข้อมูลส่วนตัวบน VM อย่า push หรือส่ง private evidence/model/credentials ให้เพื่อนโดยไม่ตรวจขอบเขตสิทธิ์
