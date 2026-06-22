# ตั้งค่า OCR Bot (Expense Tracker)

บอท LINE ที่อ่านสลิป/บิล ด้วย Tesseract OCR และบันทึกลงฐานข้อมูล

---

## ขั้นตอนติดตั้ง

### 1. ติดตั้ง Python Packages

```bash
cd backend
pip install -r requirements.txt
```

จะติดตั้ง:
- `pytesseract` — Python wrapper สำหรับ Tesseract
- `Pillow` — ไลบรารีเพื่อประมวลผลรูป

### 2. ติดตั้ง Tesseract Executable (ความสำคัญ!)

Tesseract เป็น **โปรแกรมแยกต่างหากที่ต้องติดตั้ง** ก่อนจึงจะใช้ได้

#### Windows:
1. ไปที่ https://github.com/UB-Mannheim/tesseract/wiki
2. ดาวน์โหลด **tesseract-ocr-w64-setup-xxx.exe** (เวอร์ชั่นล่าสุด)
3. รันติดตั้ง → เลือก **Thai language** ตอนติดตั้ง (สำคัญ!)
4. จดตำแหน่งที่ติดตั้ง (โดยปกติ `C:\Program Files\Tesseract-OCR`)

#### Mac:
```bash
brew install tesseract
```

#### Linux (Ubuntu/Debian):
```bash
sudo apt-get install tesseract-ocr
# ถ้ามี Thai language ให้ติดตั้ง
sudo apt-get install tesseract-ocr-tha
```

### 3. ตรวจสอบติดตั้งสำเร็จ

พิมพ์ใน Terminal/CMD:
```bash
tesseract --version
```

ควรเห็นเวอร์ชั่น Tesseract ขึ้นมา ✓

---

## การใช้งาน

### ส่งสลิป/บิลใน LINE:
1. เปิด LINE → ที่บอท
2. ส่งรูป (สลิป/บิล)
3. บอทจะ:
   - ดาวน์โหลดรูป
   - อ่าน OCR (ชื่อร้าน, เงิน, วันที่)
   - **บันทึกรอยืนยัน** ในฐานข้อมูล
   - ตอบกลับว่า "บันทึกเสร็จ"

### ยืนยันข้อมูล:
1. เข้าเว็บ http://localhost:5173
2. เมนู **"Expense Tracker"**
3. ดู "รอการยืนยัน" → ปรับแต่งเงิน/หมวดหมู่ → กดยืนยัน

### ดูประวัติ:
- ส่งข้อความ `expense` ในไลน์ → สรุปค่าใช้จ่าย
- ในเว็บดูตารางรายการทั้งหมด + สรุปตามหมวดหมู่

---

## ความแม่นยำ OCR

- **ดีสำหรับ**: สลิปจากร้านอาหาร, ร้านสะดวกซื้อ, ใบตั้งจ่าย
- **อาจผิด**: สลิปซีด่ำ, หรือรูปเบลอ
- ความแม่นยำแสดงในช่อง "ความแม่นยำ OCR: X%" ให้ตรวจสอบก่อนยืนยัน

---

## Troubleshooting

### "tesseract is not installed" หรือ "OCR ยังไม่ได้ติดตั้ง"
- ติดตั้ง Tesseract executable ตามขั้นตอน 2 ด้านบน

### Windows: "โมดูล pytesseract ไม่พบ tesseract"
- แก้ไข: หลังติดตั้ง Tesseract ให้ restart cmd/Python

### ความแม่นยำต่ำ (< 60%)
- ลองส่งรูปที่ชัดกว่า (ไม่เบลอ)
- บอทจะปรับปรุงรูปอัตโนมัติ (upscale + sharpen)

### อยากใช้ Google Vision API แทน
- ปัจจุบัน support Tesseract เท่านั้น
- Google Vision ต้องใช้ API key + paid

---

## ไฟล์ที่เกี่ยวข้อง

- `backend/ocr_helper.py` — ฟังก์ชัน OCR
- `backend/line_bot.py` — การรับไฟล์ + OCR
- `backend/routers/expenses.py` — API Expense
- `backend/models.py` — Database schema (Expense table)
- `frontend/src/pages/ExpenseTracker.tsx` — หน้า web
- `./receipts/` — โฟลเดอร์เก็บรูปสลิป

---

## คำสั่ง Expense ใน LINE

- `expense` → สรุปค่าใช้จ่าย
- **ส่งรูป** → OCR + บันทึก
- `ช่วยเหลือ` → เมนูทั้งหมด

---

**สำเร็จ!** 🎉 บอท LINE Expense Tracker พร้อมใช้งาน
