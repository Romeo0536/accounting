"""
LINE Bot router

  POST /api/line/webhook   -> รับ event จาก LINE (ตั้งค่า Webhook URL ที่นี่)
  POST /api/line/simulate  -> โหมดจำลอง: ส่งข้อความแล้วได้คำตอบของบอททันที (ทดสอบได้โดยไม่ต้องมี LINE)
  GET  /api/line/status    -> สถานะการตั้งค่า
  GET  /api/line/commands  -> รายการคำสั่งทั้งหมด
  GET/POST /api/line/config -> ตั้งค่าปลายทางแจ้งเตือนรายวัน
  POST /api/line/push-daily -> ส่งสรุปประจำวัน (กดเอง)
"""
from fastapi import APIRouter, Request, Header, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
import line_bot

router = APIRouter()


class SimulateRequest(BaseModel):
    text: str


class ConfigRequest(BaseModel):
    default_to: str


@router.get("/status")
def get_status():
    return line_bot.status_summary()


@router.get("/commands")
def list_commands():
    return {
        "commands": [
            {"command": "ช่วยเหลือ", "aliases": ["help", "เมนู", "menu"], "description": "แสดงเมนูคำสั่งทั้งหมด"},
            {"command": "สรุป", "aliases": ["dashboard", "ภาพรวม"], "description": "ภาพรวมทั้งระบบ"},
            {"command": "งานค้าง", "aliases": ["งาน", "jobs"], "description": "งานรายเดือนที่ยังไม่เสร็จ"},
            {"command": "ภาษี", "aliases": ["กำหนดยื่น", "deadline"], "description": "กำหนดยื่นภาษีที่ใกล้ถึง (30 วัน)"},
            {"command": "ค้างชำระ", "aliases": ["หนี้", "invoice"], "description": "ใบแจ้งหนี้ที่ยังไม่ชำระ"},
            {"command": "วันนี้", "aliases": ["today"], "description": "สรุปสิ่งที่ต้องทำวันนี้"},
            {"command": "เกินกำหนด", "aliases": ["overdue"], "description": "งาน/ภาษี/ใบแจ้งหนี้ที่เลยกำหนด"},
            {"command": "ลูกค้า <ชื่อ/รหัส>", "aliases": ["client"], "description": "ค้นหาลูกค้าและดูรายละเอียด"},
        ]
    }


@router.post("/simulate")
def simulate(req: SimulateRequest):
    """ทดสอบบอทโดยไม่ต้องเชื่อม LINE จริง — คืนคำตอบแบบเดียวกับที่บอทจะตอบ"""
    result = line_bot.handle_text(req.text)
    return {"reply": result["text"], "quick_replies": result.get("quick", [])}


@router.post("/webhook")
async def webhook(request: Request, x_line_signature: str = Header(default="")):
    body = await request.body()
    if not line_bot.verify_signature(body, x_line_signature):
        raise HTTPException(status_code=403, detail="invalid signature")
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    line_bot.process_events(payload.get("events", []))
    # LINE ต้องการ HTTP 200 เสมอ
    return {"ok": True}


@router.get("/config")
def get_config(db: Session = Depends(get_db)):
    return {"default_to": line_bot.get_default_recipient(db)}


@router.post("/config")
def set_config(req: ConfigRequest, db: Session = Depends(get_db)):
    line_bot._config_set(db, "line_default_to", req.default_to.strip(),
                         "ปลายทางแจ้งเตือน LINE รายวัน")
    return {"ok": True, "default_to": req.default_to.strip()}


@router.post("/push-daily")
def push_daily(db: Session = Depends(get_db)):
    return line_bot.push_daily_digest()
