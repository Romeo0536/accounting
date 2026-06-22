"""อ่านข้อมูลบิล/ใบกำกับภาษีจากไฟล์ PDF ด้วย Claude vision

ใช้ Claude API (vision) อ่านไฟล์ PDF โดยตรง แล้วบังคับให้คืนค่าเป็น JSON
ตาม schema ที่กำหนด เพื่อนำไปแสดงเป็นตาราง preview ให้ผู้ใช้ตรวจสอบก่อนบันทึก

ต้องตั้งค่า environment variable: ANTHROPIC_API_KEY
"""
import base64
import json
import os

MODEL = "claude-opus-4-8"

# schema ของข้อมูลบิลที่ต้องการดึง — บังคับให้ Claude คืน JSON ตามนี้
BILL_SCHEMA = {
    "type": "object",
    "properties": {
        "vendor_name": {"type": "string", "description": "ชื่อผู้ขาย/ผู้ออกบิล"},
        "vendor_tax_id": {"type": "string", "description": "เลขประจำตัวผู้เสียภาษี 13 หลัก (ไม่พบให้เว้นว่าง)"},
        "doc_number": {"type": "string", "description": "เลขที่ใบกำกับภาษี/ใบเสร็จ"},
        "doc_date": {"type": "string", "description": "วันที่บนเอกสาร รูปแบบ YYYY-MM-DD (ค.ศ.)"},
        "sub_total": {"type": "number", "description": "ยอดรวมก่อน VAT"},
        "vat_amount": {"type": "number", "description": "ภาษีมูลค่าเพิ่ม VAT 7%"},
        "grand_total": {"type": "number", "description": "ยอดรวมสุทธิทั้งสิ้น"},
        "items": {
            "type": "array",
            "description": "รายการสินค้า/บริการในบิล",
            "items": {
                "type": "object",
                "properties": {
                    "description": {"type": "string", "description": "ชื่อรายการ"},
                    "quantity": {"type": "number", "description": "จำนวน"},
                    "unit_price": {"type": "number", "description": "ราคาต่อหน่วย"},
                    "amount": {"type": "number", "description": "จำนวนเงินรวมของรายการ"},
                },
                "required": ["description", "amount"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["vendor_name", "doc_number", "doc_date", "grand_total", "items"],
    "additionalProperties": False,
}

PROMPT = (
    "นี่คือใบกำกับภาษี/ใบเสร็จรับเงินของไทย ดึงข้อมูลออกมาตาม schema ที่กำหนด "
    "แปลงวันที่ที่เป็นปี พ.ศ. ให้เป็น ค.ศ. รูปแบบ YYYY-MM-DD "
    "(เช่น 15 มี.ค. 2567 = 2024-03-15) "
    "ตัวเลขจำนวนเงินให้เป็น number ไม่มีเครื่องหมายคอมมาหรือสัญลักษณ์สกุลเงิน "
    "ถ้าไม่พบข้อมูลฟิลด์ใดให้ใส่ค่าว่าง (string) หรือ 0 (number)"
)


def parse_bill_pdf(pdf_bytes: bytes) -> dict:
    """อ่านบิลจาก PDF ด้วย Claude vision คืน dict ตาม BILL_SCHEMA

    raises:
        RuntimeError: ถ้าไม่ได้ตั้งค่า ANTHROPIC_API_KEY
        anthropic.APIError: ถ้าเรียก API ไม่สำเร็จ
    """
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("ยังไม่ได้ตั้งค่า ANTHROPIC_API_KEY ใน environment")

    try:
        import anthropic
    except ImportError:
        raise RuntimeError("ยังไม่ได้ติดตั้ง anthropic — รัน: pip install anthropic")

    client = anthropic.Anthropic()
    b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")

    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        output_config={"format": {"type": "json_schema", "schema": BILL_SCHEMA}},
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": b64,
                    },
                },
                {"type": "text", "text": PROMPT},
            ],
        }],
    )

    # output_config.format รับประกันว่า text block แรกเป็น JSON ที่ valid
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)
