# 🍡 น้องโมจิ — Windows Server Setup

**Spec ของคุณ: i5-9400F / RAM 32GB / GTX 750 Ti**
> เพียงพอมากสำหรับบอทนี้ — Python + SQLite ใช้ RAM น้อยกว่า 200MB

---

## ขั้นตอนทั้งหมด

### 1. ติดตั้ง Python

1. ดาวน์โหลด Python 3.11 64-bit: https://www.python.org/downloads/
2. ติ๊ก **"Add Python to PATH"** ก่อนติดตั้ง
3. ตรวจสอบ: เปิด CMD พิมพ์ `python --version`

---

### 2. ตั้งค่า .env

เปิด `linebot\.env.example` → บันทึกเป็น `linebot\.env` แล้วแก้ค่า:

```env
LINE_CHANNEL_ACCESS_TOKEN=xxxxxxx
LINE_CHANNEL_SECRET=xxxxxxx
SMTP_USER=your@gmail.com
SMTP_PASSWORD=xxxx-xxxx-xxxx-xxxx   # Gmail App Password
ADMIN_USER_IDS=Uxxxxxxxx            # User ID ของคุณใน LINE
STORAGE_PATH=D:\MochiBot\storage    # เปลี่ยนให้ชี้ไป Drive ที่มีเนื้อที่
```

---

### 3. รัน Bot ครั้งแรก (ทดสอบ)

```cmd
cd C:\path\to\accounting\linebot
deploy\windows\start.bat
```

ถ้าขึ้น `Starting น้องโมจิ on port 5001` แสดงว่า OK

---

### 4. ตั้งค่า HTTPS (เลือกวิธีใดวิธีหนึ่ง)

#### วิธี A: Cloudflare Tunnel ✅ แนะนำ (ฟรี, ไม่ต้องเปิด port)

```powershell
# รันด้วย PowerShell (Admin)
.\deploy\windows\cloudflare-tunnel.ps1
```

1. สมัคร Cloudflare ฟรีที่ https://dash.cloudflare.com
2. ไปที่ **Zero Trust → Networks → Tunnels → Create a tunnel**
3. ตั้งชื่อ `mochi-line-bot`
4. เลือก OS: **Windows** → copy คำสั่งมารัน
5. เพิ่ม **Public Hostname**:
   - Subdomain: `mochi`
   - Domain: `ชื่อ.workers.dev` (ฟรี ไม่ต้องซื้อ domain)
   - Service: `http://localhost:5001`
6. ได้ URL: `https://mochi.ชื่อ.workers.dev`

ใส่ใน LINE Developers Console:
```
Webhook URL: https://mochi.ชื่อ.workers.dev/webhook
```

#### วิธี B: มี IP สาธารณะ + nginx

1. ดาวน์โหลด nginx Windows: http://nginx.org/en/download.html
2. แตกไฟล์ไปที่ `C:\nginx\`
3. copy `deploy\nginx\nginx.conf` ไปที่ `C:\nginx\conf\nginx.conf`
4. เปิด Windows Firewall port 80/443
5. เปิด Port Forwarding บน Router: `80 → เครื่อง Server`

```cmd
C:\nginx\nginx.exe
```

---

### 5. ติดตั้งเป็น Windows Service (รันอัตโนมัติ)

1. ดาวน์โหลด **NSSM** (Non-Sucking Service Manager):
   https://nssm.cc/download → แตกไฟล์ไปที่ `C:\nssm\`

2. รัน PowerShell ในฐานะ **Administrator**:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
cd C:\path\to\accounting\linebot
.\deploy\windows\install-service.ps1
```

3. ตรวจสอบใน **Services** (services.msc) → หา `น้องโมจิ LINE Bot`

4. ตั้งให้ Start: **Automatic** → จะเริ่มทำงานทุกครั้งที่ Windows บูต

---

### 6. ตั้งค่า LINE Webhook

1. ไปที่ https://developers.line.biz/console/
2. เลือก Channel → **Messaging API**
3. ใส่ Webhook URL ตาม HTTPS URL ที่ได้
4. กด **Verify** → ต้องขึ้น Success
5. เปิด **Use webhook**
6. ปิด **Auto-reply messages** (จะส่งคำตอบเองผ่านบอท)

---

## โครงสร้างไฟล์บน Server

```
D:\MochiBot\
└── storage\
    ├── Cxxxxxxxx\          ← กลุ่ม A
    │   ├── chat_history.txt
    │   ├── 2025-06-23\
    │   │   ├── images\
    │   │   ├── videos\
    │   │   └── files\
    │   └── ...
    └── Cxxxxxxxx\          ← กลุ่ม B (อีเมลคนละกลุ่ม)
        └── ...
```

---

## การดูแล Log

```cmd
REM ดู log real-time
type C:\path\to\linebot\logs\stdout.log
type C:\path\to\linebot\logs\stderr.log

REM หรือใช้ PowerShell
Get-Content .\logs\stdout.log -Wait -Tail 50
```

---

## คำสั่ง Service ที่ใช้บ่อย

```powershell
nssm start MochiLineBot       # เริ่ม
nssm stop MochiLineBot        # หยุด
nssm restart MochiLineBot     # รีสตาร์ท
nssm status MochiLineBot      # ดูสถานะ
nssm edit MochiLineBot        # แก้ไขการตั้งค่า
```

---

## Performance บน i5-9400F / 32GB

| Resource | การใช้งานจริง |
|----------|--------------|
| CPU      | ~1-2% (idle), spike เวลารับไฟล์ |
| RAM      | ~150-200MB |
| Disk     | ขึ้นอยู่กับปริมาณไฟล์ในกลุ่ม |
| GPU      | ไม่ใช้ (GTX 750 Ti ยังว่างอยู่) |

> GTX 750 Ti เอาไว้ใช้ต่อยอดได้ เช่น AI วิเคราะห์รูปภาพ, OCR, สรุปเนื้อหาด้วย AI
