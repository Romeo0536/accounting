"""
LINE Bot - บอทผู้ช่วยสำนักงานบัญชี + Expense Tracker

ฟีเจอร์:
  - คำสั่งภาษาไทยดู stats/งาน/ภาษี/ค้าง
  - รับไฟล์สลิป/บิล → อ่าน OCR → บันทึกลงฐานข้อมูล
  - ถามผู้ใช้ยืนยันข้อมูล
  - ดูประวัติ expense
"""
import os
import json
import hmac
import base64
import hashlib
import urllib.request
import urllib.error
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

from sqlalchemy import func
from sqlalchemy.orm import Session

from database import SessionLocal
import models
import ocr_helper

LINE_API_REPLY = "https://api.line.me/v2/bot/message/reply"
LINE_API_PUSH = "https://api.line.me/v2/bot/message/push"
LINE_API_CONTENT = "https://api.line.me/v2/bot/message/{messageId}/content"

MONTH_TH = [
    "", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม",
]

RECEIPT_DIR = Path("./receipts")
RECEIPT_DIR.mkdir(exist_ok=True)


# ────────────────────────────────────────────────────────────────
# Config
# ────────────────────────────────────────────────────────────────

def get_access_token() -> str:
    return os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "").strip()


def get_channel_secret() -> str:
    return os.getenv("LINE_CHANNEL_SECRET", "").strip()


def _config_get(db: Session, key: str, default: str = "") -> str:
    row = db.query(models.AutomationConfig).filter(models.AutomationConfig.key == key).first()
    return row.value if row and row.value else default


def _config_set(db: Session, key: str, value: str, description: str = ""):
    row = db.query(models.AutomationConfig).filter(models.AutomationConfig.key == key).first()
    if row:
        row.value = value
    else:
        db.add(models.AutomationConfig(key=key, value=value, description=description))
    db.commit()


def get_default_recipient(db: Session) -> str:
    return _config_get(db, "line_default_to") or os.getenv("LINE_DEFAULT_TO", "").strip()


def is_configured() -> bool:
    return bool(get_access_token())


def status_summary() -> dict:
    db = SessionLocal()
    try:
        token = get_access_token()
        return {
            "configured": bool(token),
            "has_access_token": bool(token),
            "has_channel_secret": bool(get_channel_secret()),
            "signature_verification": bool(get_channel_secret()),
            "default_recipient": get_default_recipient(db),
            "webhook_path": "/api/line/webhook",
            "has_tesseract": ocr_helper.HAS_TESSERACT,
        }
    finally:
        db.close()


# ────────────────────────────────────────────────────────────────
# Signature verification
# ────────────────────────────────────────────────────────────────

def verify_signature(body: bytes, signature: str) -> bool:
    secret = get_channel_secret()
    if not secret:
        return True
    if not signature:
        return False
    mac = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    expected = base64.b64encode(mac).decode("utf-8")
    return hmac.compare_digest(expected, signature)


# ────────────────────────────────────────────────────────────────
# Outbound messaging
# ────────────────────────────────────────────────────────────────

def _post_line(url: str, payload: dict, extra_headers: dict = None) -> bool:
    token = get_access_token()
    if not token:
        return False
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {token}")
    if extra_headers:
        for k, v in extra_headers.items():
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return 200 <= resp.status < 300
    except urllib.error.HTTPError as e:
        print(f"[LINE] HTTP {e.code}: {e.read().decode('utf-8', 'ignore')}")
        return False
    except Exception as e:
        print(f"[LINE] error: {e}")
        return False


def reply_message(reply_token: str, messages: list) -> bool:
    return _post_line(LINE_API_REPLY, {"replyToken": reply_token, "messages": messages})


def push_message(to: str, messages: list) -> bool:
    if not to:
        return False
    return _post_line(LINE_API_PUSH, {"to": to, "messages": messages})


def download_content(message_id: str) -> bytes:
    """ดาวน์โหลดไฟล์จาก LINE (รูป/ไฟล์)"""
    token = get_access_token()
    if not token:
        return b""
    url = LINE_API_CONTENT.format(messageId=message_id)
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read()
    except Exception as e:
        print(f"[LINE] download error: {e}")
        return b""


# ────────────────────────────────────────────────────────────────
# Message builders
# ────────────────────────────────────────────────────────────────

MENU_ITEMS = ["สรุป", "งานค้าง", "ภาษี", "ค้างชำระ", "วันนี้", "expense", "ช่วยเหลือ"]


def _quick_reply(labels: list) -> dict:
    return {
        "items": [
            {
                "type": "action",
                "action": {"type": "message", "label": l[:20], "text": l},
            }
            for l in labels[:13]
        ]
    }


def text_message(text: str, quick: list = None) -> dict:
    msg = {"type": "text", "text": text}
    if quick:
        msg["quickReply"] = _quick_reply(quick)
    return msg


def _fmt_baht(n) -> str:
    return f"{float(n or 0):,.0f}"


def _fmt_date(d) -> str:
    if not d:
        return "-"
    if isinstance(d, str):
        try:
            d = datetime.fromisoformat(d).date()
        except ValueError:
            return d
    return f"{d.day} {MONTH_TH[d.month]} {d.year + 543}"


# ────────────────────────────────────────────────────────────────
# Command handlers (เดิม)
# ────────────────────────────────────────────────────────────────

def _cmd_help() -> str:
    return (
        "🤖 บอทผู้ช่วยสำนักงานบัญชี + Expense Tracker\n"
        "พิมพ์คำสั่งหรือกดปุ่มด้านล่างได้เลย\n\n"
        "📊 สรุป — ภาพรวมทั้งระบบ\n"
        "📋 งานค้าง — งานรายเดือนที่ยังไม่เสร็จ\n"
        "🧾 ภาษี — กำหนดยื่นภาษีที่ใกล้ถึง\n"
        "💰 ค้างชำระ — ใบแจ้งหนี้ที่ยังไม่จ่าย\n"
        "📅 วันนี้ — สรุปสิ่งที่ต้องทำวันนี้\n"
        "💸 expense — ดูประวัติค่าใช้จ่าย\n"
        "❓ ช่วยเหลือ — เมนูนี้\n\n"
        "📸 ส่งรูปสลิป/บิล → บอทจะอ่าน OCR + บันทึกให้"
    )


def _cmd_dashboard(db: Session) -> str:
    today = date.today()
    m, y = today.month, today.year

    total_clients = db.query(func.count(models.Client.id)).scalar() or 0
    active_clients = db.query(func.count(models.Client.id)).filter(
        models.Client.status == "active").scalar() or 0
    pending_jobs = db.query(func.count(models.MonthlyJob.id)).filter(
        models.MonthlyJob.month == m, models.MonthlyJob.year == y,
        models.MonthlyJob.status != "completed").scalar() or 0
    completed_jobs = db.query(func.count(models.MonthlyJob.id)).filter(
        models.MonthlyJob.month == m, models.MonthlyJob.year == y,
        models.MonthlyJob.status == "completed").scalar() or 0
    unpaid_invoices = db.query(func.count(models.Invoice.id)).filter(
        models.Invoice.status.in_(["sent", "overdue"])).scalar() or 0
    unpaid_amount = db.query(func.sum(models.Invoice.total)).filter(
        models.Invoice.status.in_(["sent", "overdue"])).scalar() or 0

    return (
        f"📊 ภาพรวม ณ {_fmt_date(today)}\n"
        f"ประจำเดือน {MONTH_TH[m]} {y + 543}\n"
        "──────────────\n"
        f"👥 ลูกค้าทั้งหมด {total_clients} ราย (active {active_clients})\n"
        f"📋 งานเดือนนี้: เสร็จ {completed_jobs} / ค้าง {pending_jobs}\n"
        f"💰 ค้างชำระ {unpaid_invoices} ใบ ({_fmt_baht(unpaid_amount)} บาท)"
    )


def _cmd_pending_jobs(db: Session) -> str:
    today = date.today()
    jobs = db.query(models.MonthlyJob).filter(
        models.MonthlyJob.month == today.month,
        models.MonthlyJob.year == today.year,
        models.MonthlyJob.status != "completed",
    ).all()
    if not jobs:
        return f"✅ งานเดือน {MONTH_TH[today.month]} {today.year + 543} เสร็จครบแล้ว"

    lines = [f"📋 งานค้าง ({len(jobs)} ราย)", "──────────────"]
    for j in jobs[:10]:
        name = j.client.name if j.client else f"#{j.client_id}"
        lines.append(f"• {name}")
    if len(jobs) > 10:
        lines.append(f"...และอีก {len(jobs) - 10} ราย")
    return "\n".join(lines)


def _cmd_deadlines(db: Session) -> str:
    today = date.today()
    filings = db.query(models.TaxFiling).filter(
        models.TaxFiling.status == "pending",
        models.TaxFiling.due_date >= today,
        models.TaxFiling.due_date <= today + timedelta(days=30),
    ).order_by(models.TaxFiling.due_date).limit(15).all()
    if not filings:
        return "🧾 ไม่มีกำหนดยื่นภาษีใน 30 วัน"

    lines = ["🧾 กำหนดยื่นภาษี", "──────────────"]
    for f in filings:
        name = f.client.name if f.client else f"#{f.client_id}"
        lines.append(f"• {_fmt_date(f.due_date)} — {f.filing_type}")
    return "\n".join(lines)


def _cmd_unpaid(db: Session) -> str:
    invoices = db.query(models.Invoice).filter(
        models.Invoice.status.in_(["sent", "overdue"])
    ).order_by(models.Invoice.due_date).limit(10).all()
    if not invoices:
        return "💰 ไม่มีใบแจ้งหนี้ค้างชำระ"

    total = sum(inv.total or 0 for inv in invoices)
    lines = [f"💰 ค้างชำระ ({len(invoices)} ใบ)", f"ยอดรวม {_fmt_baht(total)} บาท", "──────────────"]
    for inv in invoices[:8]:
        name = inv.client.name if inv.client else f"#{inv.client_id}"
        lines.append(f"• {inv.invoice_number} — {_fmt_baht(inv.total)}")
    return "\n".join(lines)


def _cmd_today(db: Session) -> str:
    today = date.today()
    due_today = db.query(models.TaxFiling).filter(
        models.TaxFiling.status == "pending",
        models.TaxFiling.due_date == today,
    ).all()
    pending_jobs = db.query(func.count(models.MonthlyJob.id)).filter(
        models.MonthlyJob.month == today.month,
        models.MonthlyJob.year == today.year,
        models.MonthlyJob.status != "completed").scalar() or 0

    lines = [f"📅 งานวันนี้ {_fmt_date(today)}", "──────────────"]
    if due_today:
        lines.append(f"🔴 ต้องยื่นภาษี {len(due_today)} รายการ")
        for f in due_today[:5]:
            lines.append(f"   • {f.filing_type}")
    else:
        lines.append("✅ ไม่มีกำหนดยื่นภาษี")
    lines.append(f"📋 งานเดือนนี้ค้าง: {pending_jobs} ราย")
    return "\n".join(lines)


def _cmd_expense_summary(db: Session) -> str:
    """สรุปค่าใช้จ่ายล่าสุด"""
    since = date.today() - timedelta(days=7)
    expenses = db.query(models.Expense).filter(
        models.Expense.created_at >= since,
        models.Expense.verified == True,
    ).all()

    if not expenses:
        return "💸 ไม่มีรายการค่าใช้จ่าย"

    by_cat = {}
    for e in expenses:
        cat = e.category or "อื่น"
        if cat not in by_cat:
            by_cat[cat] = 0
        by_cat[cat] += e.amount or 0

    total = sum(e.amount or 0 for e in expenses)
    lines = [f"💸 ค่าใช้จ่าย 7 วันล่าสุด", f"ยอดรวม {_fmt_baht(total)} บาท", "──────────────"]
    for cat, amt in sorted(by_cat.items(), key=lambda x: -x[1]):
        lines.append(f"• {cat}: {_fmt_baht(amt)}")
    return "\n".join(lines)


# ────────────────────────────────────────────────────────────────
# Receipt processing
# ────────────────────────────────────────────────────────────────

def process_receipt_image(image_path: str, line_user_id: str, line_group_id: str = None) -> dict:
    """อ่านสลิป และบันทึกลงฐานข้อมูล"""
    db = SessionLocal()
    try:
        # OCR
        result = ocr_helper.process_receipt(image_path)
        if not result["success"]:
            return {"success": False, "message": result["reason"]}

        data = result["data"]
        # บันทึกลงฐานข้อมูล (รอ verify)
        expense = models.Expense(
            line_user_id=line_user_id,
            line_group_id=line_group_id,
            merchant_name=data.get("merchant_name", ""),
            amount=data.get("amount", 0),
            category="อื่น",  # เดี๋ยวให้ผู้ใช้เลือก
            receipt_date=data.get("receipt_date"),
            receipt_time=data.get("receipt_time", ""),
            notes=data.get("full_text", ""),
            receipt_image_path=image_path,
            ocr_confidence=result.get("confidence", 0),
            verified=False,  # รอ verify
        )
        db.add(expense)
        db.commit()

        return {
            "success": True,
            "expense_id": expense.id,
            "merchant": data.get("merchant_name", "-"),
            "amount": data.get("amount"),
            "date": data.get("receipt_date"),
            "time": data.get("receipt_time"),
            "confidence": result.get("confidence"),
        }
    except Exception as e:
        print(f"[OCR] process error: {e}")
        return {"success": False, "message": f"Error: {str(e)}"}
    finally:
        db.close()


# ────────────────────────────────────────────────────────────────
# Command router
# ────────────────────────────────────────────────────────────────

def handle_text(text: str) -> dict:
    raw = (text or "").strip()
    low = raw.lower()
    db = SessionLocal()
    try:
        if low in ("help", "เมนู", "menu", "ช่วยเหลือ", "?", "/help", "start", "เริ่ม"):
            return {"text": _cmd_help(), "quick": MENU_ITEMS}
        if low in ("สรุป", "dashboard", "ภาพรวม"):
            return {"text": _cmd_dashboard(db), "quick": MENU_ITEMS}
        if low in ("งานค้าง", "งาน", "jobs"):
            return {"text": _cmd_pending_jobs(db), "quick": MENU_ITEMS}
        if low in ("ภาษี", "deadline", "tax"):
            return {"text": _cmd_deadlines(db), "quick": MENU_ITEMS}
        if low in ("ค้างชำระ", "หนี้", "invoice"):
            return {"text": _cmd_unpaid(db), "quick": MENU_ITEMS}
        if low in ("วันนี้", "today"):
            return {"text": _cmd_today(db), "quick": MENU_ITEMS}
        if low in ("expense", "expense summary", "ค่าใช้จ่าย"):
            return {"text": _cmd_expense_summary(db), "quick": MENU_ITEMS}

        return {
            "text": f"ไม่เข้าใจคำสั่ง \"{raw}\" 🤔\nพิมพ์ \"ช่วยเหลือ\" เพื่อดูเมนู",
            "quick": MENU_ITEMS,
        }
    finally:
        db.close()


def build_reply_messages(result: dict) -> list:
    return [text_message(result["text"], result.get("quick"))]


# ────────────────────────────────────────────────────────────────
# Webhook event processing
# ────────────────────────────────────────────────────────────────

def process_events(events: list):
    for ev in events or []:
        etype = ev.get("type")
        reply_token = ev.get("replyToken")
        user_id = ev.get("source", {}).get("userId")
        group_id = ev.get("source", {}).get("groupId")

        if etype == "follow":
            if reply_token:
                reply_message(reply_token, [text_message(
                    "สวัสดีครับ 🙏 " + _cmd_help(),
                    MENU_ITEMS,
                )])
            continue

        if etype == "message":
            msg = ev.get("message", {})
            msg_type = msg.get("type")

            if msg_type == "text":
                text = msg.get("text", "")
                result = handle_text(text)
                if reply_token:
                    reply_message(reply_token, build_reply_messages(result))

            elif msg_type == "image":
                # ดาวน์โหลดและ OCR
                message_id = msg.get("id")
                content = download_content(message_id)
                if not content:
                    reply_message(reply_token, [text_message("ดาวน์โหลดรูปไม่ได้ 😢")])
                    continue

                # เก็บไฟล์ชั่วคราว
                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False, dir=RECEIPT_DIR) as f:
                    f.write(content)
                    temp_path = f.name

                # Process OCR
                result = process_receipt_image(temp_path, user_id, group_id)

                if result["success"]:
                    msg_text = (
                        f"✓ บันทึกเสร็จ!\n"
                        f"ร้าน: {result['merchant']}\n"
                        f"เงิน: {_fmt_baht(result['amount'])} บาท\n"
                        f"วันที่: {_fmt_date(result['date'])}\n"
                        f"เวลา: {result['time']}\n"
                        f"ความแม่นยำ: {result['confidence']:.0f}%\n\n"
                        f"📱 ยืนยันข้อมูลได้ที่หน้าเว็บ"
                    )
                else:
                    msg_text = f"❌ {result['message']}"

                reply_message(reply_token, [text_message(msg_text, MENU_ITEMS)])


def build_daily_digest() -> str:
    db = SessionLocal()
    try:
        return "🌅 สรุปประจำวัน\n\n" + _cmd_today(db) + "\n\n" + _cmd_deadlines(db) + "\n\n" + _cmd_expense_summary(db)
    finally:
        db.close()


def push_daily_digest(to: str = None) -> dict:
    db = SessionLocal()
    try:
        target = to or get_default_recipient(db)
        digest = build_daily_digest()
        if not target:
            return {"sent": False, "reason": "ยังไม่ได้ตั้งค่าผู้รับ", "preview": digest}
        ok = push_message(target, [text_message(digest, MENU_ITEMS)])
        return {"sent": ok, "to": target, "preview": digest}
    finally:
        db.close()
