# รับช่วง EDRXDR-Morpheus / NEXUS SOC Copilot

เอกสารนี้ส่งต่อให้เพื่อนและ AI ใช้เริ่มตรวจงานต่อ ผล VM ด้านล่างมาจาก
คำสั่งและภาพ browser ที่ผู้ใช้ส่ง ไม่ใช่การเชื่อม VM โดยผู้จัดทำเอกสาร
ต้องตรวจสถานะปัจจุบันก่อนทำงานทุกครั้ง

## 1. เริ่มจากตรงนี้

- VM: `saiuser@172.16.30.147`
- Repo: `/home/saiuser/EDRXDR-Morpheus`
- Branch ล่าสุดที่ยืนยัน: `work/nexus-exact-ai-v1`
- HEAD ก่อนเพิ่มเอกสารนี้: `6ce591a` — บันทึกผล live candidate และการคืน GPU
- สถานะก่อนส่งต่อ: ผู้ใช้พักงาน ไม่มีสิทธิ์เปิด GPU ต่อจากข้อความส่งต่อนี้
- ใช้เอกสารนี้ร่วมกับ `training/HANDOFF-NEXUS-COPILOT-LIVE-20261024.md`
  และ `training/HANDOFF-NEXUS-P3-20261024.md`

ตรวจแบบอ่านอย่างเดียวบน VM ก่อน:

```bash
cd /home/saiuser/EDRXDR-Morpheus || exit 1
TZ=Asia/Bangkok date '+%F %T %Z'
git branch --show-current
git log -5 --oneline
git status --short
git --no-pager diff --check
systemctl --user show nexus-all-events-prod-3006.service \
  --no-pager -p ActiveState -p SubState -p MainPID
ss -ltn '( sport = :3001 or sport = :3006 or sport = :3013 or sport = :8011 )'
```

ถ้า AI เข้า VM ไม่ได้ ให้แจ้งข้อจำกัดและให้คำสั่งสั้น ๆ แก่ผู้ใช้
ห้ามสมมติผลคำสั่งหรืออ้างว่า deploy แล้วเพียงเพราะ commit สำเร็จ

## 2. ทำเสร็จและยืนยันแล้ว

### หลักฐานและ API

- Exact UID Lookup ตรวจ source index/document ID และคำนวณ canonical UID ใหม่
- Source resolver แยก Docker Compose project/service และตรวจ container ID
- Browser ส่งได้เฉพาะ UID; auth, source scope และ exact UID allowlist อยู่ฝั่ง server
- อ่าน AI แบบครบและมีขอบเขต ไม่ใช้ sampled History page ยืนยันว่าไม่มี AI score
- `matched`, `not_scored`, `conflict`, `unavailable` แยกจากกัน; คะแนนศูนย์ไม่กลายเป็น null
- Evidence API จริงผ่าน: ไม่มี auth 401, ปิด API 503, UID นอกสิทธิ์ 403
- UID ที่อนุญาตหนึ่งรายการผ่าน HTTP 200, complete=true, evidence=matched, AI=matched

### หน้าใช้งานและสรุป

- All Events มีปุ่มเปิดหลักฐานที่ตรวจใหม่ใน SOC Copilot
- สลับเหตุการณ์/คำขอล้มเหลวจะไม่แสดงผลตอบกลับเก่าทับรายการใหม่
- สรุปสร้างเมื่อผู้ใช้กดปุ่มเท่านั้น และอ่านหลักฐานใหม่ก่อนเรียกโมเดล
- คะแนนเดิมอยู่ใน evidence sidecar; ไม่ให้โมเดลสร้างหรือแก้คะแนน
- ตรวจ schema, exact citations, malformed output, tool calls, truncated output,
  ขนาด response, timeout และ cancellation
- UI ปฏิเสธการแสดงสรุปเมื่อ evidence hash ไม่ตรงกับหลักฐานที่แสดงอยู่
- Local gpt-oss-20b สร้างสรุปใหม่ผ่าน candidate จริงสำเร็จ 1 เหตุการณ์
  โดย Rule 533, Wazuh 7/15, AI เดิมประมาณ 99.9/100 และ citation ตรงรายการ
- ผลดังกล่าวเป็น `generated_unreviewed` ไม่ใช่การรับรองคุณภาพโมเดล
- สรุปเดิม 8 รายการเป็น saved report คนละส่วนกับการสร้างสรุปใหม่
- Automated response OFF; ไม่มีการเทรนในรอบนี้

### การทดสอบ

- ชุด API/core/provider/config/UI รวม 10 test scripts และ strict TypeScript
  ผ่านใน isolated staging บน VM ก่อนเพิ่ม draft API/UI
- แพตช์สถานะแถบ UI ล่าสุดผ่าน syntax และ UI regression แบบจำลอง
- Browser จริงผ่านการเลือก UID ที่อนุญาต/ปฏิเสธและสร้างสรุปใหม่ 1 รายการ
- การเปลี่ยนแถบสถานะล่าสุดยังไม่ได้ตรวจ browser จริง

## 3. Commit ที่เกี่ยวข้อง

| Commit | งาน |
|---|---|
| `aeb008f` | P3 baseline, data readiness และ protected rules |
| `98bf97e` | ลดส่วนเมนูและ header ตามที่ผู้ใช้ต้องการ |
| `63d4b21` | authenticated/scoped evidence API |
| `502f302` | All Events เปิดหลักฐานใน Copilot |
| `96401fe` | evidence-bound summary core |
| `2463f0d` | local provider พร้อม reservation gate |
| `03d02b8` | เชื่อม draft API และปุ่มสร้างสรุป |
| `02347a8` | แถบสถานะเปลี่ยนตามการสร้างสรุป |
| `6ce591a` | ผล live candidate และ GPU closure |

## 4. Runtime ไม่เท่ากับ repo HEAD

- Dashboard หลักที่ตรวจพบคือพอร์ต 3006:
  `/home/saiuser/nexus-uid-candidate-wgpajvXL`
- พอร์ต 3001 ตรวจล่าสุดเป็น inactive/dead และเชื่อมต่อไม่ได้
- งาน Copilot ใหม่ทดสอบใน candidate แยกพอร์ต 3013 ไม่ได้ deploy ไป 3006
- หลังจบรอบตรวจแล้วพอร์ต 3013 และ 8011 ไม่มี listener
- ต้องตรวจ runtime จริงซ้ำ อย่า build ทับ `.next` ที่กำลังให้บริการ
- History มี dependency นอก repo เช่น query script และ auth เดิมใน
  `/home/saiuser/nexus-history-preview-20261020/`
- Runtime model/venv/cache อยู่ `/mnt/nexus-copilot-mQTssj/` ไม่อยู่ใน Git
- Checkout repo อย่างเดียวจึงยังไม่ใช่ระบบที่ deploy พร้อมใช้งาน

## 5. ปิดรอบ GPU แล้ว

- GPU ที่ใช้ทดสอบ: H100 UUID `GPU-61a1dd9b-a3c2-86dc-15b9-1277b5b949bb`
- สิทธิ์รอบที่จบนี้ถึง 05:00 วันที่ 24 ต.ค. 2026 เวลาไทย
  ไม่ใช่สิทธิ์ใช้งานครั้งถัดไป
- ผู้ใช้หยุด LLM ก่อนกำหนด และตรวจยืนยันว่าไม่มี GPU process ของเรา
- เหลือ LuckyFive PID 189036 ใช้ 808 MiB ณ การตรวจครั้งนั้น
  PID นี้เป็นข้อมูลประวัติ ห้ามนำไปสั่งหยุดหรือถือว่าเป็น PID ปัจจุบัน
- พอร์ต 8011 ปิด และไฟล์ reservation ไม่มีแล้วในการตรวจสุดท้าย
- จะใช้ GPU ใหม่ต้องมี reservation ใหม่และตรวจ guard/การใช้เครื่องร่วมใหม่
- Adapter ตรวจข้อมูล reservation แต่ไม่ได้ตรวจ scheduler หรือ GPU occupancy แทนผู้ใช้
- ตัว launcher รอบ 24 ต.ค. กำหนดวัน/เวลาตายตัว ห้ามนำมารันซ้ำโดยไม่ทบทวน

## 6. จุดค้างและงานถัดไป

1. เพิ่มการบันทึกสรุปใหม่แบบถาวรและผลตรวจ Analyst
   - ปัจจุบันสรุปใหม่อยู่ในหน้า browser และไม่ได้ถูกบันทึกถาวร
   - ผูก UID, evidence hash, model/revision, prompt version และเวลาสร้าง
   - เก็บต้นฉบับ immutable; แยกการตัดสิน/หมายเหตุของผู้ตรวจ
   - เริ่มจากข้อมูลสังเคราะห์และ offline tests ไม่ต้องใช้ GPU
2. ตรวจแถบสถานะรุ่น `02347a8` ใน browser โดยใช้ mock ไม่ต้องเรียกโมเดลซ้ำ
3. ประเมินคุณภาพสรุปหลายชนิดเหตุการณ์โดย Analyst
   - ผ่าน flow 1 เหตุการณ์ไม่ได้หมายถึง semantic accuracy ผ่าน
4. ทบทวน production access: auth เดิมเป็น shared operator principal
   ยังไม่มี individual-user RBAC และ rate limit เป็น per-process
5. จัด deployment dependencies และ candidate/rollback ที่ตรวจได้ก่อนเสนอ deploy
6. การเปิดโมเดลจริงต้องตรวจ artifact/revision และ GPU UUID ให้ตรงกับ reservation

ห้ามเพิ่ม UID เข้า allowlist อัตโนมัติจาก browser หรือถือว่าปรากฏใน History
แล้วได้รับอนุญาตให้ส่งเข้า LLM โดยทันที API สร้างสรุปปิดโดยค่าเริ่มต้น
(`NEXUS_COPILOT_DRAFT` ต้องเปิดอย่างเจาะจงใน candidate ที่ตรวจแล้ว)

## 7. P3 และข้อจำกัดคุณภาพโมเดลเดิม

P3 เป็นงานประเมิน/ออกแบบข้อมูลแยกจาก SOC Copilot ไม่ใช่งานฝึกที่เริ่มแล้ว
รายละเอียดอ้าง `training/HANDOFF-NEXUS-P3-20261024.md`

- Snapshot 19,994 UID / 90 rules; archive integrity 14/14 ผ่าน
  ไม่ใช่การยืนยัน activity provenance หรือสิทธิ์นำเข้า train
- provenance ของหลายกลุ่มยังไม่ทราบ; ห้ามสรุปว่า benign/attack/lab จากเวลาอย่างเดียว
- Rule 550 เป็น protected quarantine rule; Rule 2901 เป็น protected validation rule
  ห้ามย้ายเข้า train เพื่อแก้คะแนน แม้เป็น UID ใหม่
- รักษา validation/quarantine/reserve เดิม; ไม่เปลี่ยน threshold หรือฝึกโมเดลอัตโนมัติ
- context-v2-balanced เป็น weak severity baseline ไม่ใช่ attack probability
  คุณภาพเดิมยังไม่ผ่านเกณฑ์ ห้ามนำผล parity/hash มาอ้างเป็นความแม่นยำ

## 8. ข้อจำกัดการทำงานบน VM

- รักษา Git WIP และ untracked เดิม ห้าม reset/clean/checkout ทับ หรือ `git add .`
- Untracked ที่ยังคงอยู่: `history/`, `uid_lookup/`, handoff/evidence เดิมบางชุด
  ห้าม add รวมโดยไม่ review โดยเฉพาะข้อมูลส่วนตัว/logs
- ห้ามเปลี่ยน driver/network หรือหยุด shared stack/process ของเพื่อน
- ห้าม build ทับ runtime `.next` หรือเปลี่ยน shared systemd state โดยไม่อนุญาต
- BlueField/rshim ต้อง inactive/dead/disabled; automated response ต้อง OFF
- ห้าม reset/consume offsets เพิ่มเอง; รักษา supervisor lag/offset เดิม
- Lab Agent003 ยังพักไว้ ไม่อนุญาตแก้ FIM config หรือ restart agent จาก handoff นี้
- ห้ามส่ง secrets/raw logs/datasets/weights ออกภายนอกหรือ commit เข้า Git
- การทำงานต่อจากเอกสารนี้ไม่ถือว่าอนุญาต GPU/training/deploy ใหม่

## 9. ส่งต่อให้ AI

ให้ AI อ่านไฟล์นี้และ handoff ที่อ้างถึง เริ่มตรวจ HEAD/WIP/runtime แบบ read-only
ก่อน จากนั้นทำงานบันทึกสรุปและ Analyst review ด้วย synthetic tests ในพื้นที่แยก
อย่าเริ่ม GPU, inference, training, deploy หรือ resume supervisor อัตโนมัติ
แจ้งผลที่ตรวจจริงและข้อจำกัดให้ชัดเจน แยกคำสั่ง VM กับ Windows PowerShell
