# เริ่มรับช่วงงานที่นี่ — 1 พฤศจิกายน 2026

## โครงการนี้ทำอะไร

EDRXDR–Morpheus–NEXUS มีงานสองส่วนที่ต้องแยกกัน:

1. ระบบ NEXUS รับและแสดงเหตุการณ์ Wazuh/คะแนน Severity
2. งานทดลอง BERT v4 ทำนาย MITRE tactics จากข้อมูลระดับ attack step

BERT v4 ยังไม่ได้แทนโมเดล Severity บน Dashboard
ผลทดลอง BERT จึงไม่ใช่ผลความแม่นยำของ NEXUS ทั้งระบบ

## ตอนนี้ถึงไหน

สถานะล่าสุดที่ผู้ใช้ส่งมายืนยัน:
- Branch: work/nexus-exact-ai-v1
- Commit: 3945620
- Experiment B ฝึกเสร็จและตรวจ hash checkpoint ครบ 8/8
- Development: macro F1 0.1727, micro F1 0.2557, exact match 3/72
- คุณภาพยังไม่พร้อม production
- ตรวจ CPU/GPU และการกลับลำดับ source แล้ว
- พบ audit key ที่มีชื่อเทคนิคอยู่ใน config ต้นทาง
- ยังไม่พิสูจน์ว่า key เป็นสาเหตุของผลทำนายหรือเป็น label leakage
- Final holdout family 6 ยังไม่ได้ใช้
- ผู้ใช้พักงานไว้

วันที่ในชื่อเอกสารนี้ไม่ใช่การยืนยันสถานะ runtime ใหม่
ต้องตรวจสถานะปัจจุบันก่อนทำงานต่อ

## งานถัดไปเพียงงานเดียว

เตรียมข้อกำหนดและตัวตรวจสอบการทดลองปิดบัง audit key
บน development โดยแยกจากข้อมูลเดิม

ยังไม่เริ่มรันโมเดล:
- เก็บข้อมูลต้นฉบับและ labels เดิม
- ไม่เติมข้อความท้ายเข้ามาแทนส่วนที่ปิดบัง
- กำหนดวิธีจัดการ key ที่ถูกตัดกลางข้อความให้ชัด
- เปรียบเทียบรายเหตุการณ์กับผลเดิม
- ไม่เปิด final holdout เพื่อเลือกวิธี
- ไม่ฝึกใหม่หรือ deploy จากเอกสารส่งต่อนี้

## โฟลเดอร์ที่ใช้

VM: saiuser@172.16.30.147
Repo: /home/saiuser/EDRXDR-Morpheus
งานทดลอง: /home/saiuser/EDRXDR-BERTv4-work
Checkpoint: runs/bert-v4-planB-expB-16719 ภายในงานทดลอง
Dataset: datasets/bert-v4-planB-16695 ภายในงานทดลอง

Runtime NEXUS ที่เคยตรวจ:
พอร์ต 3006, /home/saiuser/nexus-uid-candidate-wgpajvXL
ต้องตรวจใหม่ก่อนใช้ข้อมูลนี้ ห้ามถือว่า repo คือรุ่นที่ deploy อยู่

## เริ่มอ่านแค่สองไฟล์นี้

ภายใน /home/saiuser/EDRXDR-Morpheus:
1. training/HANDOFF-PROJECT-20261030-COMPLETE.md
   ภาพรวมระบบและตำแหน่งงาน
2. training/BERT-V4-AUDIT-KEY-PROVENANCE-20261031.md
   ข้อค้นพบล่าสุดและข้อจำกัด

รายละเอียดวิธีทดลองที่ยังเป็นร่าง:
training/BERT-V4-PREPROCESSING-PROPOSAL-DRAFT-20261031.md

## ข้อห้าม

- รักษา untracked/WIP เดิม ห้าม reset/clean/เขียนทับ หรือ git add .
- ห้ามเปิด final holdout family 6 หรือแก้ frozen datasets/labels
- ห้ามเริ่ม training/GPU จนยืนยันสิทธิ์และช่วงจองใหม่
- ห้ามหยุด process ของ LuckyFive หรือเปลี่ยน shared stack/driver/network
- ห้าม reset offsets หรือ build ทับ runtime .next
- BlueField/rshim และ automated response ต้อง OFF
- ไม่ส่ง raw logs/datasets/weights/private predictions เข้าแชทหรือ Git

## คำสั่งเริ่มตรวจ — อ่านอย่างเดียว

cd /home/saiuser/EDRXDR-Morpheus || exit 1
date -Is
git branch --show-current
git log -5 --oneline
git status --short
git diff --check

ส่งผลตรวจและสรุปความเข้าใจก่อนเริ่มแก้ไข
หากผู้ใช้ยังไม่สั่งเริ่มงาน ให้หยุดหลังตรวจสถานะ
