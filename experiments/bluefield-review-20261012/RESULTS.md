# BlueField isolated review — 2026-10-12 (Asia/Bangkok)

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
- งานถัดไป: ตรวจ frontend ล่าสุด แล้วเพิ่มมุมมอง BlueField แบบข้อมูลย้อนหลังจาก index ทดลอง; ยังไม่เปิด service หรือเชื่อม schema ทดลองเข้า live normalizer

อัปเดตนี้ใช้แทนข้อความเก่าที่บอกว่า BlueField ยังวน restart หรือยังไม่เคยทดสอบ Kafka/OpenSearch; ข้อความเก่าด้านล่างเก็บไว้เป็นประวัติ
<!-- handoff-20261012-verified:end -->

## Scope and evidence provenance

This directory archives separate experimental source trees. It does not replace bluefield-agent/, normalizer/, service units or any build directory used by a service. No driver, interface, broker or production configuration was changed by these experiments.

The following VM results were supplied by the operator in this conversation, not independently rerun on Windows. Original VM logs and JSONL must be copied into evidence/ using the accompanying collection script; they are not fabricated or reconstructed here.

## Observed results

- Original publisher service referenced a missing ~/EDRXDR-Morpheus/build/bluefield-agent/bluefield_monitor and repeatedly restarted. No claim is made that this service has been repaired or stopped.
- Review monitor: 9 synthetic C tests passed, DOCA 3.2.3005 build passed, and bounded sampling produced 6 real records (two interfaces, three rounds). Both interfaces were down; carrier was null with Invalid argument; all six counters were readable zero values.
- Monitor evidence directory: /home/saiuser/edrxdr-bluefield-nullcheck.Bn44DZ.
- Offline normalizer: 14 tests passed on the VM and 6 real file records normalized. All carrier values stayed null; two initial rx_bytes deltas were null (first_sample), and four subsequent deltas were computed zero. No broker access occurred.
- Normalizer evidence directory: /home/saiuser/edrxdr-bluefield-normalize.udX6v2.
- The monitor run-check.sh packaged here adds TMPDIR under its output directory. The successful VM run used the previous script with TMPDIR explicitly set by the operator. C source and tests are unchanged; the updated wrapper itself has not been independently rerun on the VM.

Existing component README validation sections describe their original packaging-time status. This document records the later operator-supplied VM results without rewriting historical claims.

## Remaining work

No live Kafka, Morpheus, OpenSearch integration, traffic test, GPU parity or real outage recovery was performed in this experiment. The current live Normalizer still coerces null to zero; do not send this new schema to its topic. Before integration, define a separate topic/index and consumer group, preserve the nullable contract through downstream processing, and coordinate interface ownership with the shared VM/network team. Do not enable ports or deploy the test binary to the service path merely to populate the Dashboard.

## Publisher restart-loop containment

- Verified at: 2026-10-12T21:00:06.917891+07:00
- Service stopped and disabled; state: inactive/dead/disabled.
- Missing service binary remains unresolved; telemetry publishing is not restored.
- Experimental code has not been deployed to the live service.
- Re-enable only after integration validation and deployment review.
