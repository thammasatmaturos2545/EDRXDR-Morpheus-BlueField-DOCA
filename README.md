# EDRXDR Morpheus BlueField DOCA

ระบบ **EDR/XDR Intelligent Threat Detection Pipeline** สำหรับตรวจจับและวิเคราะห์ภัยคุกคามด้านเครือข่าย โดยพัฒนาบนเทคโนโลยีของ NVIDIA และระบบ Event Streaming

โปรเจกต์นี้ใช้ **NVIDIA BlueField-3 + NVIDIA DOCA** สำหรับเก็บ Network Telemetry แล้วส่งข้อมูลผ่าน **Apache Kafka** ไปยัง **NVIDIA Morpheus** เพื่อทำ GPU-accelerated Threat Analysis จากนั้นบันทึกผลลง **OpenSearch** และแสดงผลผ่าน **Next.js Security Dashboard**

> หมายเหตุ: ปัจจุบันส่วน NVIDIA Morpheus ยังรอการแก้ไข H100 GPU Fabric จากฝั่ง HGX/KVM Host โดยส่วนอื่นของ Pipeline สามารถทำงานได้แล้ว

---

## Architecture

```text
              NVIDIA BlueField-3
                       │
                       ▼
                 NVIDIA DOCA
                       │
                       ▼
              bluefield_monitor
                       │
                   JSON Event
                       │
                       ▼
            Kafka: bluefield-events
                       │
                       ▼
                  Normalizer
                       │
                       ▼
            Kafka: morpheus-input
                       │
                       ▼
              NVIDIA Morpheus
             GPU Threat Analysis
                       │
                       ▼
            Kafka: morpheus-output
                       │
                       ▼
                    Indexer
                       │
                       ▼
                  OpenSearch
                       │
                       ▼
                  Next.js API
             /api/events /api/status
                       │
                       ▼
               EDRXDR Dashboard
```

---

## เทคโนโลยีที่ใช้

| เทคโนโลยี | หน้าที่ |
|---|---|
| NVIDIA BlueField-3 | Network/DPU Telemetry Source |
| NVIDIA DOCA | เข้าถึงและประมวลผลข้อมูลจาก BlueField |
| NVIDIA DPDK | High-performance packet processing |
| Apache Kafka | Event Streaming / Message Broker |
| Python | Normalizer และ Indexer |
| C | BlueField / DOCA Monitor |
| NVIDIA Morpheus | GPU-accelerated Security Analytics |
| NVIDIA H100 | GPU สำหรับ Morpheus |
| OpenSearch | จัดเก็บและค้นหา Security Events |
| Next.js | Security Dashboard |
| TypeScript / React | Frontend |
| Docker Compose | จัดการ Services |

---

## โครงสร้างโปรเจกต์

```text
EDRXDR-Morpheus/
│
├── bluefield-agent/
│   ├── meson.build
│   └── src/
│       ├── bluefield_monitor.c
│       └── bluefield_probe.c
│
├── frontend/
│   ├── src/
│   │   └── app/
│   │       ├── api/
│   │       │   ├── events/
│   │       │   └── status/
│   │       └── page.tsx
│   ├── package.json
│   └── package-lock.json
│
├── normalizer/
│   ├── Dockerfile
│   ├── normalizer.py
│   └── requirements.txt
│
├── indexer/
│   ├── Dockerfile
│   ├── indexer.py
│   └── requirements.txt
│
├── morpheus/
│   └── start.sh
│
├── compose.yml
├── .env.example
├── .gitignore
└── README.md
```

---

# การทำงานของ Pipeline

## 1. NVIDIA BlueField-3

BlueField-3 ทำหน้าที่เป็น Network Telemetry Source

อุปกรณ์ที่ใช้ในการพัฒนา:

```text
NVIDIA BlueField-3
Integrated ConnectX-7
```

ตรวจสอบอุปกรณ์:

```bash
lspci | grep -Ei "BlueField|Mellanox|ConnectX"
```

ตรวจสอบ DOCA Device:

```bash
sudo /opt/mellanox/doca/tools/doca_caps --list-devs
```

ตัวอย่าง:

```text
PCI: 0000:06:11.0
ibdev_name: mlx5_0

PCI: 0000:06:11.1
ibdev_name: mlx5_1
```

---

## 2. NVIDIA DOCA

DOCA ใช้สำหรับเข้าถึง BlueField device และเก็บข้อมูล Network Telemetry

ตัวอย่างข้อมูลที่ได้จาก `bluefield_monitor`:

```json
{
  "timestamp": "2026-09-16T13:46:30Z",
  "source": "bluefield",
  "ibdev": "mlx5_0",
  "interface": "enp6s17f0np0",
  "rx_packets": 0,
  "tx_packets": 0,
  "rx_bytes": 0,
  "tx_bytes": 0,
  "rx_errors": 0,
  "tx_errors": 0
}
```

---

## 3. Apache Kafka

Kafka ทำหน้าที่เป็น Event Streaming Platform ของระบบ

Pipeline ใช้ Topic หลัก 3 ตัว:

```text
bluefield-events
morpheus-input
morpheus-output
```

### bluefield-events

รับข้อมูลดิบจาก BlueField Monitor

```text
BlueField
   ↓
DOCA
   ↓
bluefield_monitor
   ↓
bluefield-events
```

### morpheus-input

รับข้อมูลที่ผ่าน Normalizer แล้ว เพื่อรอ NVIDIA Morpheus วิเคราะห์

```text
bluefield-events
      ↓
Normalizer
      ↓
morpheus-input
```

### morpheus-output

รับผล Threat Analysis จาก NVIDIA Morpheus

```text
Morpheus
   ↓
morpheus-output
```

---

# Normalizer

Normalizer ทำหน้าที่แปลงข้อมูล BlueField ให้อยู่ใน Common Security Event Schema

ตัวอย่าง:

```json
{
  "timestamp": "2026-09-16T13:46:30Z",
  "event_type": "network_telemetry",
  "source_type": "bluefield",
  "sensor": "nvidia-bluefield-3",
  "ibdev": "mlx5_0",
  "interface": "enp6s17f0np0",
  "rx_packets": 0,
  "tx_packets": 0,
  "delta_rx_packets": 0,
  "delta_tx_packets": 0
}
```

ข้อมูลจะถูกส่งต่อไปยัง:

```text
morpheus-input
```

---

# NVIDIA Morpheus

NVIDIA Morpheus เป็นส่วนสำหรับทำ GPU-accelerated Security Analytics

Flow ที่ออกแบบไว้คือ:

```text
morpheus-input
      ↓
from-kafka
      ↓
deserialize
      ↓
GPU Processing / Inference
      ↓
Threat Score / Classification
      ↓
serialize
      ↓
to-kafka
      ↓
morpheus-output
```

Morpheus ใช้ Container:

```text
nvcr.io/nvidia/morpheus/morpheus:25.06-runtime
```

ตรวจสอบ GPU Fabric ก่อนเปิด Morpheus:

```bash
nvidia-smi -q -i 0 | grep -i -A 3 Fabric
```

สถานะที่ต้องการ:

```text
Fabric
    State  : Completed
    Status : Success
```

จากนั้นเปิด Morpheus:

```bash
docker compose --profile gpu up -d morpheus
```

ดู Log:

```bash
docker compose logs -f morpheus
```

---

# สถานะ H100 GPU ปัจจุบัน

ปัจจุบัน H100 สามารถมองเห็นได้จาก VM:

```text
NVIDIA H100 80GB HBM3
```

แต่ GPU Fabric ยังเป็น:

```text
Fabric
    State  : In Progress
    Status : N/A
```

ทำให้ Morpheus / cuDF ไม่สามารถ Initialize CUDA ได้ และเกิด:

```text
cudaErrorSystemNotReady: system not yet initialized
```

ปัญหานี้ต้องแก้จากฝั่ง **HGX / KVM Host / NVIDIA Fabric Manager**

เมื่อแก้สำเร็จต้องได้:

```text
State  : Completed
Status : Success
```

จากนั้นจึงสามารถเปิด Morpheus จริงได้

---

# OpenSearch

OpenSearch ใช้สำหรับเก็บ Security Events หลังจากออกจาก `morpheus-output`

ตรวจสอบ:

```bash
curl http://localhost:9200
```

ดู Index:

```bash
curl "http://localhost:9200/_cat/indices?v"
```

Security Events จะถูกเก็บใน:

```text
edrxdr-events-YYYY.MM.DD
```

ค้นหาข้อมูล:

```bash
curl "http://localhost:9200/edrxdr-events-*/_search?pretty"
```

---

# Dashboard

Frontend พัฒนาด้วย:

```text
Next.js
React
TypeScript
Tailwind CSS
```

ติดตั้ง Dependencies:

```bash
cd frontend
npm install
```

เปิด Development Server:

```bash
npm run dev -- --hostname 0.0.0.0
```

เข้า Dashboard:

```text
http://HOST_IP:3000
```

---

## Dashboard แสดงข้อมูล

Dashboard สามารถแสดง:

- สถานะ NVIDIA BlueField-3
- สถานะ NVIDIA DOCA
- สถานะ Kafka
- สถานะ Normalizer
- สถานะ NVIDIA Morpheus
- สถานะ H100 GPU Fabric
- สถานะ Indexer
- สถานะ OpenSearch
- Security Events
- Threat Score
- Threat Classification
- BlueField RX/TX Packets
- BlueField RX/TX Bytes
- Network Interface
- DOCA Device
- Recent Security Events

ระบบ Refresh ข้อมูลทุกประมาณ 5 วินาที

---

# API

## Security Events API

```text
GET /api/events
```

ใช้ดึง Security Events จาก OpenSearch

---

## Infrastructure Status API

```text
GET /api/status
```

ตัวอย่าง:

```json
{
  "bluefield": true,
  "doca": true,
  "kafka": true,
  "normalizer": true,
  "opensearch": true,
  "indexer": true,
  "morpheus": false,
  "gpuFabric": "waiting"
}
```

---

# การติดตั้ง

## 1. Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/EDRXDR-Morpheus-BlueField-DOCA.git
```

เข้าโปรเจกต์:

```bash
cd EDRXDR-Morpheus-BlueField-DOCA
```

---

## 2. ตั้งค่า Environment

สร้าง `.env`:

```bash
cp .env.example .env
```

แก้:

```bash
nano .env
```

กำหนด IP ของ VM/Host:

```env
HOST_IP=YOUR_VM_IP
```

ตัวอย่าง:

```env
HOST_IP=172.16.30.147
```

ไฟล์ `.env` จะไม่ถูก Upload ขึ้น GitHub

---

## 3. ตั้งค่า DPDK

```bash
export PKG_CONFIG_PATH=/opt/mellanox/dpdk/lib/x86_64-linux-gnu/pkgconfig:$PKG_CONFIG_PATH
```

ตรวจสอบ:

```bash
pkg-config --modversion libdpdk
pkg-config --modversion doca-common
pkg-config --modversion doca-flow
```

---

## 4. ตั้งค่า HugePages

```bash
echo 1024 | sudo tee \
/sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
```

สร้าง Mount Point:

```bash
sudo mkdir -p /mnt/huge
```

Mount:

```bash
sudo mount \
-t hugetlbfs \
-o pagesize=2M \
nodev \
/mnt/huge
```

ตรวจสอบ:

```bash
grep -i Huge /proc/meminfo
```

---

## 5. Build BlueField Agent

```bash
mkdir -p build
```

```bash
meson setup \
  build/bluefield-agent \
  bluefield-agent
```

Compile:

```bash
ninja -C build/bluefield-agent
```

ทดสอบ BlueField:

```bash
./build/bluefield-agent/bluefield_probe
```

รัน Monitor:

```bash
./build/bluefield-agent/bluefield_monitor
```

---

## 6. เปิด Infrastructure

```bash
docker compose up -d --build
```

ตรวจสอบ:

```bash
docker compose ps
```

Core services:

```text
edrxdr-kafka
edrxdr-normalizer
edrxdr-indexer
edrxdr-opensearch
```

---

## 7. ตรวจ Kafka

ดู BlueField Events:

```bash
docker exec edrxdr-kafka \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic bluefield-events \
  --max-messages 2
```

ดู Morpheus Input:

```bash
docker exec edrxdr-kafka \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic morpheus-input \
  --max-messages 2
```

---

# สถานะโปรเจกต์ปัจจุบัน

| Component | Status |
|---|---|
| NVIDIA BlueField-3 | ✅ ทำงาน |
| NVIDIA DOCA | ✅ ทำงาน |
| DPDK Runtime | ✅ ทำงาน |
| BlueField Probe | ✅ ทำงาน |
| BlueField Monitor | ✅ ทำงาน |
| Kafka | ✅ ทำงาน |
| Normalizer | ✅ ทำงาน |
| `bluefield-events` | ✅ ทำงาน |
| `morpheus-input` | ✅ ทำงาน |
| NVIDIA Morpheus | ⏳ รอ H100 Fabric |
| H100 GPU Fabric | ⏳ In Progress |
| `morpheus-output` | ✅ Topic พร้อม |
| Indexer | ✅ ทำงาน |
| OpenSearch | ✅ ทำงาน |
| Next.js API | ✅ ทำงาน |
| Security Dashboard | ✅ ทำงาน |

---

# Pipeline ปัจจุบัน

```text
BlueField-3 ✅
     ↓
NVIDIA DOCA ✅
     ↓
bluefield_monitor ✅
     ↓
Kafka: bluefield-events ✅
     ↓
Normalizer ✅
     ↓
Kafka: morpheus-input ✅
     ↓
NVIDIA Morpheus ⏳
     ↓
Kafka: morpheus-output
     ↓
Indexer ✅
     ↓
OpenSearch ✅
     ↓
Next.js Dashboard ✅
```

---

# เป้าหมายของโปรเจกต์

เป้าหมายของระบบคือสร้าง EDR/XDR Security Pipeline ที่สามารถนำข้อมูล Network Telemetry จาก NVIDIA BlueField มาวิเคราะห์ด้วย GPU Security Analytics และแสดงผลผ่าน Dashboard แบบ Real-time

เมื่อ H100 GPU Fabric พร้อม ระบบจะสามารถเปิด NVIDIA Morpheus เพื่อทำ Threat Analysis จริงใน Pipeline ได้

---

## License

โปรเจกต์นี้จัดทำขึ้นเพื่อการศึกษา การวิจัย และการพัฒนาต้นแบบด้าน Cybersecurity, EDR/XDR, NVIDIA BlueField, DOCA และ NVIDIA Morpheus
