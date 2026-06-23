@echo off
chcp 65001 >nul
title น้องโมจิ LINE Bot

cd /d "%~dp0.."

REM Check .env exists
if not exist ".env" (
    copy ".env.example" ".env"
    echo.
    echo [!] สร้าง .env แล้ว -- กรุณาใส่ค่า Token ก่อนรันใหม่
    echo [!] แก้ไขไฟล์: %~dp0..\.env
    echo.
    pause
    exit /b 1
)

REM Create venv if not exists
if not exist "venv\" (
    echo [*] สร้าง virtual environment...
    python -m venv venv
)

REM Activate and install
call venv\Scripts\activate.bat
pip install -q -r requirements.txt

REM Create storage folder
if not exist "storage\" mkdir storage

echo.
echo  ================================================
echo   น้องโมจิ LINE Bot - Starting on port 5001
echo  ================================================
echo.
python app.py

pause
