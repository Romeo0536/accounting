import os
import json
import logging
import re
import threading
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)
TZ = pytz.timezone(os.environ.get('TIMEZONE', 'Asia/Bangkok'))

BILL_PROMPT = """วิเคราะห์ภาพนี้ว่าเป็นบิล / ใบเสร็จ / ใบแจ้งหนี้ / invoice / quotation หรือไม่

ถ้าใช่ ให้สกัดข้อมูลทั้งหมดที่อ่านได้และตอบเป็น JSON รูปแบบนี้เท่านั้น:
{
  "is_bill": true,
  "bill_type": "receipt หรือ invoice หรือ quotation",
  "merchant": "ชื่อร้าน/บริษัท",
  "merchant_address": "ที่อยู่ (ถ้ามี ไม่มีใส่ว่าง)",
  "tax_id": "เลขประจำตัวผู้เสียภาษี (ถ้ามี ไม่มีใส่ว่าง)",
  "receipt_no": "เลขที่ใบเสร็จ/invoice (ถ้ามี ไม่มีใส่ว่าง)",
  "date": "วันที่ รูปแบบ DD/MM/YYYY (ถ้าไม่พบใส่ว่าง)",
  "items": [
    {"name": "ชื่อรายการ", "qty": 1, "unit_price": 0.00, "amount": 0.00}
  ],
  "subtotal": 0.00,
  "discount": 0.00,
  "tax_rate": 7,
  "tax_amount": 0.00,
  "total": 0.00,
  "payment_method": "เงินสด / โอน / บัตรเครดิต / QR Code (ถ้าไม่ชัดใส่ว่าง)",
  "note": "หมายเหตุ (ถ้ามี ไม่มีใส่ว่าง)"
}

ถ้าไม่ใช่บิล/ใบเสร็จ ตอบ: {"is_bill": false}

ตอบเป็น JSON เท่านั้น ห้ามมีข้อความอื่นนอกจาก JSON"""

TEXT_BILL_PROMPT = """ข้อความต่อไปนี้คือข้อมูลที่สกัดจากไฟล์ PDF วิเคราะห์ว่าเป็นบิล/ใบเสร็จ/ใบแจ้งหนี้หรือไม่

ข้อความ:
{text}

ถ้าใช่ ให้สกัดข้อมูลและตอบเป็น JSON รูปแบบนี้เท่านั้น:
{
  "is_bill": true,
  "bill_type": "receipt หรือ invoice หรือ quotation",
  "merchant": "ชื่อร้าน/บริษัท",
  "merchant_address": "ที่อยู่ (ถ้ามี ไม่มีใส่ว่าง)",
  "tax_id": "เลขประจำตัวผู้เสียภาษี (ถ้ามี ไม่มีใส่ว่าง)",
  "receipt_no": "เลขที่ใบเสร็จ/invoice (ถ้ามี ไม่มีใส่ว่าง)",
  "date": "วันที่ รูปแบบ DD/MM/YYYY (ถ้าไม่พบใส่ว่าง)",
  "items": [
    {"name": "ชื่อรายการ", "qty": 1, "unit_price": 0.00, "amount": 0.00}
  ],
  "subtotal": 0.00,
  "discount": 0.00,
  "tax_rate": 7,
  "tax_amount": 0.00,
  "total": 0.00,
  "payment_method": "เงินสด / โอน / บัตรเครดิต (ถ้าไม่ชัดใส่ว่าง)",
  "note": "หมายเหตุ (ถ้ามี ไม่มีใส่ว่าง)"
}

ถ้าไม่ใช่บิล/ใบเสร็จ ตอบ: {"is_bill": false}

ตอบเป็น JSON เท่านั้น"""


def _get_model():
    api_key = os.environ.get('GEMINI_API_KEY', '')
    if not api_key or api_key.startswith('AIzaSyx'):
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model_name = os.environ.get('GEMINI_MODEL', 'gemini-2.0-flash')
        return genai.GenerativeModel(model_name)
    except ImportError:
        logger.error('google-generativeai package not installed')
        return None


def _parse_json(text: str) -> dict:
    text = text.strip()
    # Strip markdown code fences if Gemini wraps JSON in ```
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    m = re.search(r'\{.*\}', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            pass
    return {'is_bill': False}


def analyze_image(image_path: str) -> dict:
    """Send image to Gemini Vision and extract bill data."""
    model = _get_model()
    if not model:
        logger.debug('GEMINI_API_KEY not configured, skipping bill analysis')
        return {'is_bill': False}

    try:
        from PIL import Image
        img = _open_image_resized(image_path)
        if img is None:
            return {'is_bill': False}
        response = model.generate_content([BILL_PROMPT, img])
        return _parse_json(response.text)
    except Exception as e:
        logger.error(f'Gemini image analysis error: {e}')
        return {'is_bill': False}


def analyze_pdf(pdf_path: str) -> dict:
    """Extract text from PDF then send to Gemini for bill extraction."""
    model = _get_model()
    if not model:
        return {'is_bill': False}

    text = _extract_pdf_text(pdf_path)
    if not text or len(text.strip()) < 20:
        logger.info(f'PDF text too short or empty: {pdf_path}')
        return {'is_bill': False}

    try:
        response = model.generate_content(TEXT_BILL_PROMPT.format(text=text[:4000]))
        return _parse_json(response.text)
    except Exception as e:
        logger.error(f'Gemini PDF analysis error: {e}')
        return {'is_bill': False}


def _open_image_resized(path: str):
    """Open image with PIL, resize if >4 MB to stay within Gemini limits."""
    try:
        from PIL import Image
        import io
        img = Image.open(path)
        if os.path.getsize(path) > 4 * 1024 * 1024:
            img.thumbnail((2000, 2000))
            buf = io.BytesIO()
            fmt = 'JPEG' if path.lower().endswith(('.jpg', '.jpeg')) else 'PNG'
            img.save(buf, format=fmt, quality=85)
            buf.seek(0)
            img = Image.open(buf)
        return img
    except Exception as e:
        logger.error(f'Failed to open image: {e}')
        return None


def _extract_pdf_text(path: str) -> str:
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages[:5]:  # max 5 pages
                t = page.extract_text()
                if t:
                    text_parts.append(t)
        return '\n'.join(text_parts)
    except Exception as e:
        logger.error(f'PDF text extraction failed: {e}')
        return ''


def format_bill_reply(data: dict, filename: str) -> str:
    """Format extracted bill data as a LINE message."""
    bill_type_map = {
        'receipt': 'ใบเสร็จรับเงิน',
        'invoice': 'ใบแจ้งหนี้',
        'quotation': 'ใบเสนอราคา',
    }
    bill_type = bill_type_map.get(data.get('bill_type', 'receipt'), 'บิล')

    lines = [f'🧾 พบ{bill_type}ค่ะ!']

    if data.get('merchant'):
        lines.append(f'\n🏪 ร้าน/บริษัท: {data["merchant"]}')
    if data.get('date'):
        lines.append(f'📅 วันที่: {data["date"]}')
    if data.get('receipt_no'):
        lines.append(f'🔢 เลขที่: {data["receipt_no"]}')
    if data.get('tax_id'):
        lines.append(f'🆔 เลขภาษี: {data["tax_id"]}')

    items = data.get('items', [])
    if items:
        lines.append('\n📋 รายการ:')
        for item in items[:15]:  # max 15 items shown
            name = item.get('name', '')
            qty = item.get('qty', '')
            amount = item.get('amount', 0)
            qty_str = f' x{qty}' if qty and qty not in (1, '1', '') else ''
            lines.append(f'  • {name}{qty_str}  {amount:,.2f} ฿')
        if len(items) > 15:
            lines.append(f'  ...และอีก {len(items)-15} รายการ')

    lines.append('─' * 28)

    if data.get('subtotal') and data.get('subtotal') != data.get('total'):
        lines.append(f'💵 ราคาก่อนภาษี: {data["subtotal"]:>10,.2f} ฿')
    if data.get('discount') and data['discount'] > 0:
        lines.append(f'🏷️ ส่วนลด:       {data["discount"]:>10,.2f} ฿')
    if data.get('tax_amount') and data['tax_amount'] > 0:
        rate = data.get('tax_rate', 7)
        lines.append(f'🏛️ ภาษี {rate}%:    {data["tax_amount"]:>10,.2f} ฿')
    total = data.get('total', 0)
    if total:
        lines.append(f'✅ ยอดสุทธิ:      {total:>10,.2f} ฿')

    if data.get('payment_method'):
        lines.append(f'\n💳 ชำระ: {data["payment_method"]}')
    if data.get('note'):
        lines.append(f'📝 หมายเหตุ: {data["note"]}')

    lines.append(f'\n💾 บันทึกข้อมูลแล้วค่ะ 🍡')
    return '\n'.join(lines)


def process_bill_async(line_bot_api, group_id: str, filepath: str,
                       filename: str, file_type: str = 'image'):
    """Run bill analysis in a background thread and push result to group."""
    def _worker():
        from database import save_bill
        from linebot.models import TextSendMessage

        if file_type == 'pdf':
            data = analyze_pdf(filepath)
        else:
            data = analyze_image(filepath)

        if not data.get('is_bill'):
            return  # Not a bill, do nothing

        try:
            save_bill(group_id, data, filepath)
            _save_bill_json(filepath, data)
            reply_text = format_bill_reply(data, filename)
            line_bot_api.push_message(group_id, TextSendMessage(text=reply_text))
            logger.info(f'Bill extracted from {filename} in group {group_id}')
        except Exception as e:
            logger.error(f'Failed to save/push bill result: {e}')

    t = threading.Thread(target=_worker, daemon=True)
    t.start()


def _save_bill_json(image_path: str, data: dict):
    """Save extracted bill data as .json next to the original file."""
    json_path = os.path.splitext(image_path)[0] + '_bill.json'
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f'Failed to save bill JSON: {e}')
