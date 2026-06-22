"""
OCR Helper — อ่านข้อมูลจากไฟล์สลิป/บิล ด้วย Tesseract

ต้องติดตั้ง:
  pip install pytesseract pillow

และติดตั้ง Tesseract executable:
  Windows: ดาวน์โหลดจาก https://github.com/UB-Mannheim/tesseract/wiki
  Mac: brew install tesseract
  Linux: sudo apt-get install tesseract-ocr
"""
import os
import re
from datetime import datetime
from pathlib import Path

try:
    import pytesseract
    from PIL import Image, ImageEnhance
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False


def _find_tesseract_path():
    """ค้นหา Tesseract executable"""
    common_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    for p in common_paths:
        if os.path.exists(p):
            return p
    return None


def _setup_tesseract():
    """ตั้งค่า path ถ้าต้อง (Windows)"""
    if not HAS_TESSERACT:
        return False
    try:
        path = _find_tesseract_path()
        if path:
            pytesseract.pytesseract.pytesseract_cmd = path
        return True
    except Exception:
        return False


def _enhance_image(image_path: str) -> Image.Image:
    """ปรับปรุงคุณภาพรูป เพื่อให้ OCR อ่านได้ดีขึ้น"""
    img = Image.open(image_path).convert("RGB")
    # ขยายขนาด 2x (upscale)
    img = img.resize((img.width * 2, img.height * 2), Image.Resampling.LANCZOS)
    # เพิ่มความชัด
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(2)
    # เพิ่มความสว่าง
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(1.2)
    return img


def extract_text(image_path: str) -> tuple[str, float]:
    """
    อ่านข้อความจากรูป ใช้ Tesseract
    คืน (text, confidence)
    """
    if not HAS_TESSERACT or not _setup_tesseract():
        return "", 0.0

    try:
        img = _enhance_image(image_path)
        # อ่าน OCR
        text = pytesseract.image_to_string(img, lang="tha+eng")
        # ประเมินความเชื่อมั่น (แบบง่าย: ดูว่าหาเลขได้ไหม)
        confidence = 50.0 if any(c.isdigit() for c in text) else 20.0
        return text, confidence
    except Exception as e:
        print(f"[OCR] Error: {e}")
        return "", 0.0


def parse_receipt_info(text: str) -> dict:
    """
    ถอด pattern สำคัญจากข้อความ:
    - ชื่อร้าน / บริษัท
    - จำนวนเงิน (ตัวเลข)
    - วันเวลา
    """
    info = {
        "merchant_name": "",
        "amount": None,
        "receipt_date": None,
        "receipt_time": "",
    }

    lines = text.split("\n")

    # หาจำนวนเงิน (ตัวเลข + . + ตัวเลข หรือแค่ตัวเลข)
    amounts = re.findall(r"\d+[.,]\d{1,2}|\d+", text)
    if amounts:
        # เอาตัวเลขที่ใหญ่ที่สุด (ส่วนใหญ่คือราคา)
        amounts_num = [float(a.replace(",", ".")) for a in amounts]
        info["amount"] = max(amounts_num)

    # หาวันเวลา (ระบบง่าย: หาเลขตั้ง 4 หลัก + เลขสองหลัก + เลขสองหลัก)
    date_pattern = r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})|(\d{1,2}[-/]\d{1,2}[-/]\d{4})"
    dates = re.findall(date_pattern, text)
    if dates:
        try:
            date_str = dates[0][0] or dates[0][1]
            # ลองแปลง
            for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"]:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    info["receipt_date"] = dt.date()
                    break
                except ValueError:
                    continue
        except Exception:
            pass

    # หาเวลา (HH:MM)
    time_pattern = r"(\d{1,2}):(\d{2})"
    times = re.findall(time_pattern, text)
    if times:
        info["receipt_time"] = f"{times[0][0]}:{times[0][1]}"

    # หาชื่อร้าน (ประมาณ: บรรทัดแรกหรือหาคำสำคัญ)
    # ลองหาคำไทยจำนวนมาก ในบรรทัดแรก
    for line in lines:
        line = line.strip()
        if len(line) > 5 and len(line) < 100:
            # เลือกบรรทัดแรกที่ดูเหมือนชื่อร้าน
            info["merchant_name"] = line
            break

    return info


def process_receipt(image_path: str) -> dict:
    """Process สลิป/บิล โดยใช้ OCR"""
    if not os.path.exists(image_path):
        return {
            "success": False,
            "reason": "ไฟล์ไม่พบ",
            "data": {},
        }

    # อ่าน OCR
    text, confidence = extract_text(image_path)
    if not text:
        return {
            "success": False,
            "reason": "อ่านรูปไม่ได้ (OCR fail)",
            "data": {},
        }

    # ถอด info
    info = parse_receipt_info(text)
    info["full_text"] = text  # เก็บข้อความทั้งหมด

    return {
        "success": True,
        "data": info,
        "confidence": confidence,
    }


# ตรวจสอบ Tesseract เมื่อ import
if not _setup_tesseract():
    print("[OCR] ⚠️ Tesseract ยังไม่ได้ติดตั้ง หรือหาไม่เจอ")
    print("[OCR] ติดตั้งด้วย: pip install pytesseract pillow")
    print("[OCR] แล้วติดตั้ง Tesseract executable")
