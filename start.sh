#!/bin/bash
# สตาร์ทระบบบริหารจัดการสำนักงานบัญชี

echo "=== ระบบบริหารจัดการสำนักงานบัญชี ==="

# Start backend
echo ">> เริ่มต้น Backend API (port 8000)..."
cd "$(dirname "$0")/backend"

# โหลดค่า LINE Bot จาก .env ถ้ามี (ไม่ต้องใช้ dependency เพิ่ม)
if [ -f .env ]; then
  set -a; . ./.env; set +a
  echo ">> โหลดค่าจาก backend/.env แล้ว"
fi
uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Start frontend
echo ">> เริ่มต้น Frontend (port 5173)..."
cd "$(dirname "$0")/frontend"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✓ Backend:  http://localhost:8000"
echo "✓ Frontend: http://localhost:5173"
echo "✓ API Docs: http://localhost:8000/docs"
echo ""
echo "กด Ctrl+C เพื่อหยุดระบบ"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
