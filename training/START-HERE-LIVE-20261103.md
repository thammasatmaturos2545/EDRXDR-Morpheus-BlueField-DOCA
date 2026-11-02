# เพื่อนรับช่วง: อ่านไฟล์นี้ก่อน

**งานพักอยู่ — อย่าเปิด GPU/training/logging หรือ collector อัตโนมัติ**

## ตอนนี้มีอะไรใช้งานแล้ว

- VM `saiuser@172.16.30.147`; repo `/home/saiuser/EDRXDR-Morpheus`
- Branch ล่าสุด `work/nexus-exact-ai-v1`; code baseline `70dc9a4`
  HEAD หลังเพิ่มเอกสารอาจใหม่กว่า ให้ตรวจ Git อีกครั้ง
- NEXUS พอร์ต **3006** เพิ่มหน้า **Model Lab** แล้ว ใช้ผล sample/replay
- **ยังไม่ได้ทำ DFP/Ransomware ตรวจจับสดสำเร็จ และยังไม่ได้แทน BERT**
- Archive probe จบและคืน `logall_json=no` แล้ว ไม่เปิดเก็บต่อเอง

## ต้องเริ่มทำอะไร

1. อ่าน [handoff รายละเอียด](HANDOFF-NEXUS-LIVE-NEXT-20261103.md)
2. ตรวจ Git/runtime แบบ read-only ตามคำสั่งใน handoff รักษา WIP/untracked
3. งานพัฒนาถัดไปคือเชื่อม stream reader กับ feature extractor และ durable ACK
   ใน candidate แยก พร้อมทดสอบ rotation/gap recovery จริง
4. ข้อมูล archives ตอนนี้มีเพียง **5 windows** จาก probe ที่มี Manager restart
   ยังไม่ใช่ normal baseline; ต้องวางแผนและขอสิทธิ์เก็บข้อมูลตัวแทนรอบใหม่
5. ห้ามฝึก/สลับโมเดลจน source, feature contract, validation และสิทธิ์พร้อม

## ระวัง 3 เรื่อง

- Archives ของ003: 171recordsแต่17legacyUIDgroups ห้ามdedupด้วยUIDของalertsเดิม
  adapterรักษา171recordsแล้ว;อย่าแก้UIDของNEXUSหรือผสมdatasetสองsource
- Stream cursorผ่าน21testsและactual frozen replay204records แต่ยังไม่deployสด
- Agent003Active/004Disconnectedในsnapshotล่าสุด;CUDA999และRansomwareclassmappingยังค้าง

**ข้อมูล/โมเดล/หลักฐานอยู่บน VM ใน private folders ที่ระบุใน handoff**
ไม่ส่ง raw logs/datasets/weights/secrets เข้าchat/Git ไม่reset/clean ไม่git add .
