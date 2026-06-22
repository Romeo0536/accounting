@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === ระบบบริหารจัดการสำนักงานบัญชี ===
echo.

REM ---- ตรวจว่ามี Python หรือยัง ----
where python >nul 2>nul
if errorlevel 1 (
  echo [!] ไม่พบ Python บนเครื่อง
  echo     กรุณาติดตั้งก่อนที่: https://www.python.org/downloads/
  echo     ** ตอนติดตั้ง ให้ติ๊กถูกช่อง "Add Python to PATH" ด้วย **
  echo.
  pause
  exit /b
)

REM ---- ตรวจว่ามี Node.js หรือยัง ----
where node >nul 2>nul
if errorlevel 1 (
  echo [!] ไม่พบ Node.js บนเครื่อง
  echo     กรุณาติดตั้งก่อนที่: https://nodejs.org  (กดปุ่มฝั่งซ้ายที่เขียนว่า LTS)
  echo.
  pause
  exit /b
)

REM ---- ไฟล์ใส่ API key ----
if not exist ".env" (
  copy ".env.example" ".env" >nul
  echo.
  echo [!] สร้างไฟล์ .env ให้แล้ว และกำลังเปิดให้
  echo     นำ API key ของคุณมาวางแทนข้อความ "ใส่-key-ของคุณตรงนี้" แล้วบันทึก
  echo     (คัดลอก key ได้ที่ https://console.anthropic.com)
  echo     จากนั้นดับเบิลคลิกไฟล์นี้อีกครั้ง
  echo.
  notepad ".env"
  pause
  exit /b
)

REM ---- โหลดค่า key จากไฟล์ .env ----
setlocal enabledelayedexpansion
for /f "usebackq eol=# tokens=1,* delims==" %%a in (".env") do (
  set "%%a=%%b"
)
if "!ANTHROPIC_API_KEY!"=="" echo [!] ยังไม่ได้ใส่ API key — ฟีเจอร์อ่านบิล PDF จะยังใช้ไม่ได้
if "!ANTHROPIC_API_KEY!"=="ใส่-key-ของคุณตรงนี้" echo [!] ยังไม่ได้ใส่ API key — ฟีเจอร์อ่านบิล PDF จะยังใช้ไม่ได้

REM ---- ติดตั้งสิ่งที่จำเป็น (ครั้งแรกจะนานหน่อย) ----
echo.
echo ^>^> กำลังติดตั้งโปรแกรมที่จำเป็น...
python -m pip install -q -r backend\requirements.txt
if not exist "frontend\node_modules" (
  echo ^>^> ติดตั้งส่วนหน้าเว็บ ครั้งแรกใช้เวลาสักครู่...
  pushd frontend
  call npm install
  popd
)

REM ---- เปิดระบบ(เปิด 2 หน้าต่าง อย่าปิดระหว่างใช้งาน) ----
echo.
echo ^>^> กำลังเปิดระบบ...
cd /d "%~dp0backend"
start "Backend - ห้ามปิดหน้าต่างนี้" cmd /k uvicorn main:app --reload --host 0.0.0.0 --port 8000
cd /d "%~dp0frontend"
start "Frontend - ห้ามปิดหน้าต่างนี้" cmd /k npm run dev
cd /d "%~dp0"

echo.
echo รอสักครู่ ระบบจะเปิดเว็บให้อัตโนมัติที่ http://localhost:5173
timeout /t 8 >nul
start http://localhost:5173
echo.
echo เสร็จแล้ว! ถ้าต้องการหยุดระบบ ให้ปิดหน้าต่างสีดำทั้ง 2 อัน
pause
