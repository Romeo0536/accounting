#!/bin/bash
# สตาร์ทระบบบริหารจัดการสำนักงานบัญชี (แบบสำเร็จรูป — ติดตั้งและเปิดให้อัตโนมัติ)

cd "$(dirname "$0")"
echo "=== ระบบบริหารจัดการสำนักงานบัญชี ==="

# ---- 1) ตรวจไฟล์ใส่ API key ----
if [ ! -f ".env" ]; then
  cp ".env.example" ".env"
  echo ""
  echo "⚠️  สร้างไฟล์ .env ให้แล้ว"
  echo "    กรุณาเปิดไฟล์ชื่อ  .env  แล้วนำ API key ของ Anthropic มาวาง"
  echo "    (สมัครและคัดลอก key ได้ที่ https://console.anthropic.com)"
  echo "    เสร็จแล้วรันคำสั่งนี้อีกครั้ง"
  echo ""
  exit 1
fi

# โหลดค่าในไฟล์ .env เข้าระบบ
set -a
. ./.env
set +a

if [ -z "$ANTHROPIC_API_KEY" ] || [ "$ANTHROPIC_API_KEY" = "ใส่-key-ของคุณตรงนี้" ]; then
  echo ""
  echo "⚠️  ยังไม่ได้ใส่ API key — เปิดไฟล์ .env แล้ววาง key ของคุณก่อนนะครับ"
  echo "    (ฟีเจอร์อ่านบิล PDF จะใช้ไม่ได้ถ้าไม่มี key)"
  echo ""
fi

# ---- 2) ติดตั้งสิ่งที่ขาด (ครั้งแรกจะนานหน่อย) ----
echo ">> ตรวจสอบ/ติดตั้งโปรแกรมที่จำเป็น..."
pip install -q -r backend/requirements.txt
if [ ! -d "frontend/node_modules" ]; then
  echo ">> ติดตั้งส่วนหน้าเว็บ (ครั้งแรกใช้เวลาสักครู่)..."
  (cd frontend && npm install)
fi

# ---- 3) เปิดระบบ ----
echo ">> เริ่มต้น Backend API (port 8000)..."
(cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000) &
BACKEND_PID=$!

echo ">> เริ่มต้น Frontend (port 5173)..."
(cd frontend && npm run dev) &
FRONTEND_PID=$!

echo ""
echo "✓ เปิดเว็บได้ที่:  http://localhost:5173"
echo "✓ Backend:        http://localhost:8000"
echo ""
echo "กด Ctrl+C เพื่อหยุดระบบ"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
