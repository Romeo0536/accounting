# 🍡 น้องโมจิ — LINE Bot Setup Guide

## สิ่งที่ต้องมีก่อน

1. **LINE Developers Account** — https://developers.line.biz
2. **Gmail App Password** — https://myaccount.google.com/apppasswords
3. **Python 3.10+**
4. **ngrok** (สำหรับ local dev) — https://ngrok.com

---

## ขั้นตอนการตั้งค่า

### 1. สร้าง LINE Messaging API Channel

1. ไปที่ https://developers.line.biz/console/
2. สร้าง Provider ใหม่ (ถ้ายังไม่มี)
3. สร้าง Channel → **Messaging API**
4. คัดลอก **Channel Secret** และ **Channel Access Token** (Issue one)

### 2. ตั้งค่า `.env`

```bash
cp .env.example .env
```

แก้ไขค่าใน `.env`:
```
LINE_CHANNEL_ACCESS_TOKEN=ใส่ token ที่ได้
LINE_CHANNEL_SECRET=ใส่ secret ที่ได้
SMTP_USER=อีเมลที่ใช้ส่ง@gmail.com
SMTP_PASSWORD=app-password-16-ตัว
ADMIN_USER_IDS=user_id_ของคุณ (ดูได้จาก LINE Developers)
```

### 3. รัน Bot

```bash
./start.sh
```

### 4. ตั้งค่า Webhook (local dev ด้วย ngrok)

```bash
# Terminal 2
ngrok http 5001
```

คัดลอก HTTPS URL เช่น `https://xxxx.ngrok.io`  
ไปที่ LINE Developers Console → Messaging API → Webhook URL:  
```
https://xxxx.ngrok.io/webhook
```

เปิด **Use webhook** และกด **Verify**

### 5. เพิ่มบอทเข้ากลุ่ม LINE

ไปที่ LINE Developers Console → LINE Official Account features  
เปิด **Allow bot to join group chats**

---

## คำสั่งในกลุ่ม LINE

| คำสั่ง | คำอธิบาย |
|--------|----------|
| `!ช่วยเหลือ` | แสดงคำสั่งทั้งหมด |
| `!ตั้งค่าอีเมล xxx@gmail.com` | ตั้งอีเมลรับไฟล์ของกลุ่มนี้ |
| `!เปิดแจ้งเตือน` / `!ปิดแจ้งเตือน` | เปิด/ปิดแจ้งเตือนทางอีเมล |
| `!เปิดบันทึก` / `!ปิดบันทึก` | เปิด/ปิดการบันทึกไฟล์ |
| `!ตั้งเวลา 14:30 ข้อความ` | ตั้งนัดหมายส่งข้อความวันนี้ |
| `!ตั้งเวลา 2025-12-31 23:59 สุขสันต์ปีใหม่!` | ตั้งนัดหมายวันที่ระบุ |
| `!นัดหมาย` | ดูรายการนัดหมายทั้งหมด |
| `!ยกเลิก 3` | ยกเลิกนัดหมาย #3 |
| `!สถิติ` | ดูสถิติรูป/วิดีโอ/ไฟล์ 7 วัน |
| `!ส่งสรุป` | ส่งสรุปประจำวันทางอีเมลทันที |
| `!สถานะ` | ดูการตั้งค่าปัจจุบันของกลุ่ม |
| `!เพิ่มแอดมิน Uxxxx` | เพิ่มแอดมินใหม่ |

---

## โครงสร้างไฟล์ที่บันทึก

```
storage/
└── {GROUP_ID}/
    ├── chat_history.txt          ← ประวัติแชท (ไม่แยกวัน)
    ├── 2025-01-15/
    │   ├── images/               ← รูปภาพวันนั้น
    │   ├── videos/               ← วิดีโอวันนั้น
    │   ├── files/                ← ไฟล์แนบวันนั้น
    │   └── audio/                ← เสียงวันนั้น
    └── 2025-01-16/
        └── ...
```

---

## Deploy บน Server จริง

### ด้วย Systemd

```ini
# /etc/systemd/system/mochi-bot.service
[Unit]
Description=น้องโมจิ LINE Bot
After=network.target

[Service]
WorkingDirectory=/path/to/linebot
ExecStart=/path/to/linebot/venv/bin/python app.py
Restart=always
User=www-data

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable mochi-bot
sudo systemctl start mochi-bot
```

### ด้วย Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5001
CMD ["python", "app.py"]
```

---

## Gmail App Password

1. ไปที่ https://myaccount.google.com/security
2. เปิด **2-Step Verification** ก่อน
3. ไปที่ **App passwords**
4. เลือก Mail → Other → ตั้งชื่อ "น้องโมจิ Bot"
5. คัดลอก password 16 ตัวมาใส่ใน `.env`
