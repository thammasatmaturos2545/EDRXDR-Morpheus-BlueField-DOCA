# EDRXDR · Morpheus · NEXUS

ระบบวิเคราะห์เหตุการณ์ความปลอดภัยจาก Wazuh และ endpoint พร้อมหน้า NEXUS สำหรับดูหลักฐานและทบทวนผล

**สถานะ ณ 6 พฤศจิกายน 2026:** อยู่ระหว่างพัฒนาและประเมิน DFP/endpoint บน Agent003 ยังไม่ได้แทน live BERT และยังไม่เปิด automated response

เอกสารนี้สรุปงานบน branch `work/nexus-exact-ai-v1` การนำเอกสารเข้า `main` ไม่ได้รวมซอร์สงานพัฒนาหรือ deploy ระบบ

## เริ่มอ่านที่นี่

- [สถานะระบบเทียบกับสถาปัตยกรรมเป้าหมาย](PROJECT-STATUS.md)
- [ส่งต่องานล่าสุดและข้อจำกัดขณะพักงาน](https://github.com/thammasatmaturos2545/EDRXDR-Morpheus-BlueField-DOCA/blob/work/nexus-exact-ai-v1/training/HANDOFF-PAUSED-DFP-ENDPOINT-20261105.md)
- [ขอบเขต source checkpoint และงานทดลอง](https://github.com/thammasatmaturos2545/EDRXDR-Morpheus-BlueField-DOCA/blob/work/nexus-exact-ai-v1/training/experiments/agent003-source-checkpoint-20261106/UPLOAD-SCOPE.md)

## ระบบมีอะไรแล้ว

| ส่วนงาน | สถานะที่มีหลักฐาน |
| --- | --- |
| Wazuh และเส้นทางรับส่งเหตุการณ์ | มีระบบเดิมใช้งานอยู่ การรับข้อมูลครบถ้วนสำหรับโมเดลยังต้องประเมิน |
| NEXUS Dashboard | มี Model Lab และ DFP Diagnostic สำหรับดูผล sample/replay และผลวิเคราะห์ที่บันทึกไว้ |
| DFP | โมเดล CPU ทดลองแยกสองบัญชีผ่าน fit/save/reload/scoring แต่ยังไม่ผ่านการรับรองคุณภาพ |
| Endpoint file behavior | ทดสอบการส่งเหตุการณ์ในพื้นที่แยกผ่าน ยังไม่ใช่ผลวัดความแม่นยำการตรวจ ransomware |
| Ransomware classifier | มี sample/replay; live telemetry และ class mapping ยังไม่ผ่านรับรอง |
| Human Review | มี foundation, candidate publisher และ preview บัญชีผู้ทบทวน; ยังไม่ใช่ workflow แจ้งเตือนจริงที่ผ่านรับรอง |

ผล replay 773 รายการ, FIM 12/12 และ controlled modifications 20/20 เป็นคนละขอบเขตกับ detection quality ห้ามใช้แทน accuracy, recall หรือ false-positive rate

## โครงสร้าง repository

| ตำแหน่ง | หน้าที่ |
| --- | --- |
| `frontend/` | ซอร์ส Dashboard และ API บน branch นี้ |
| `normalizer/` | การแปลงเหตุการณ์ |
| `indexer/` | การตรวจสัญญาข้อมูลและจัดเก็บผล |
| `morpheus/` | ซอร์สงาน inference/pipeline; ต้องตรวจสถานะ deploy แยกจากการมีไฟล์ใน Git |
| `history/`, `uid_lookup/` | เครื่องมือประวัติเหตุการณ์และการอ้างอิง identity |
| `training/` | เอกสารส่งต่อ การทดลอง และหลักฐานที่อนุญาตให้เผยแพร่ |
| `training/experiments/agent003-source-checkpoint-20261106/` | สำเนาซอร์ส candidate และ draft เพื่อส่งต่อ ไม่ใช่ production entry point |

## งานที่ต้องทำต่อ

1. ตรวจสถานะ observer รอบเดิมและ runtime แบบอ่านอย่างเดียวก่อนเริ่มงาน
2. รับรอง source coverage และ baseline พร้อมกำหนด chronological evaluation
3. ประเมินโมเดลและเลือก threshold ตาม protocol ที่อนุมัติ
4. เชื่อม trusted alert publisher กับ named reviewers ภายใต้ขอบเขตที่ยืนยันแล้ว
5. ให้เจ้าของเลือกพื้นที่ endpoint ที่ต้องป้องกันก่อน deploy การเฝ้าระวังจริง

ขอบเขตปัจจุบันไม่ใช้ BlueField, Agent004 พักไว้ และ Network อยู่นอก scope ไม่เปิด final holdout หรือเริ่ม GPU/training/logging/collector/observer รอบใหม่จากคำแนะนำใน README นี้

## การส่งต่อและประวัติ

การ push ซอร์สไม่ใช่การ deploy รุ่นที่รันจริงอาจอยู่ใน release directory แยกต่างหาก ห้ามรัน helper เก่าอัตโนมัติหรือถือว่า candidate ที่อยู่ใน Git เปิดใช้งานแล้ว

เก็บ raw logs, datasets, weights, keys และทะเบียนผู้ใช้ private ไว้นอก Git รักษา staged/untracked/WIP เดิมทั้งหมด

[README ของ main ก่อน PR นี้](https://github.com/thammasatmaturos2545/EDRXDR-Morpheus-BlueField-DOCA/blob/7b0b8f3cf871061111836cc72fd4cc593eea7897/README.md) อาจมีสถานะและขั้นตอนของรุ่นเก่า ให้ใช้เอกสารเริ่มอ่านด้านบนสำหรับการรับช่วงปัจจุบัน
