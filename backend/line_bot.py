"""
LINE Bot - บอทผู้ช่วยสำนักงานบัญชี

ออกแบบให้ "ใช้งานได้ทันที" :
  - ไม่ต้องติดตั้ง dependency เพิ่ม (ใช้เฉพาะ standard library)
  - ถ้ายังไม่ได้ตั้งค่า LINE token ก็ยังทดสอบผ่านหน้าเว็บ (โหมดจำลอง) ได้
  - คำสั่งทั้งหมดเป็นภาษาไทย + มี Quick Reply ให้กดง่าย

ตั้งค่าเมื่อพร้อมใช้งานจริง (ผ่าน environment variable):
  LINE_CHANNEL_ACCESS_TOKEN = Channel access token (จาก LINE Developers)
  LINE_CHANNEL_SECRET       = Channel secret (ใช้ตรวจสอบ signature)
  LINE_DEFAULT_TO           = userId/groupId ปลายทางสำหรับการแจ้งเตือนรายวัน (ตั้งทีหลังก็ได้)
"""
import os
import json
import hmac
import base64
import hashlib
import urllib.request
import urllib.error
from datetime import date, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from database import SessionLocal
import models

LINE_API_REPLY = "https://api.line.me/v2/bot/message/reply"
LINE_API_PUSH = "https://api.line.me/v2/bot/message/push"

MONTH_TH = [
    "", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม",
]


# ────────────────────────────────────────────────────────────────
# Config helpers
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
    """ปลายทางแจ้งเตือนรายวัน — เก็บใน DB ก่อน ถ้าไม่มีค่อยอ่านจาก env"""
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
        }
    finally:
        db.close()


# ────────────────────────────────────────────────────────────────
# Signature verification (LINE Messaging API)
# ────────────────────────────────────────────────────────────────

def verify_signature(body: bytes, signature: str) -> bool:
    """
    ตรวจสอบ X-Line-Signature
    ถ้ายังไม่ได้ตั้ง channel secret -> ข้าม (โหมดพัฒนา) เพื่อให้ลองใช้ได้ทันที
    """
    secret = get_channel_secret()
    if not secret:
        return True
    if not signature:
        return False
    mac = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    expected = base64.b64encode(mac).decode("utf-8")
    return hmac.compare_digest(expected, signature)


# ────────────────────────────────────────────────────────────────
# Outbound messaging (ใช้ urllib ไม่ต้องลง requests)
# ────────────────────────────────────────────────────────────────

def _post_line(url: str, payload: dict) -> bool:
    token = get_access_token()
    if not token:
        # ยังไม่ได้ตั้งค่า — ไม่ถือเป็น error เพื่อให้ทดสอบโหมดจำลองได้
        return False
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {token}")
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


# ────────────────────────────────────────────────────────────────
# Message builders
# ────────────────────────────────────────────────────────────────

MENU_ITEMS = ["สรุป", "งานค้าง", "ภาษี", "ค้างชำระ", "วันนี้", "ลูกค้า", "ช่วยเหลือ"]


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
# Command handlers — แต่ละฟังก์ชันคืน "ข้อความ" (str)
# ────────────────────────────────────────────────────────────────

def _cmd_help() -> str:
    return (
        "🤖 บอทผู้ช่วยสำนักงานบัญชี\n"
        "พิมพ์คำสั่งหรือกดปุ่มด้านล่างได้เลย\n\n"
        "📊 สรุป — ภาพรวมทั้งระบบ\n"
        "📋 งานค้าง — งานรายเดือนที่ยังไม่เสร็จ\n"
        "🧾 ภาษี — กำหนดยื่นภาษีที่ใกล้ถึง\n"
        "💰 ค้างชำระ — ใบแจ้งหนี้ที่ยังไม่จ่าย\n"
        "📅 วันนี้ — สรุปสิ่งที่ต้องทำวันนี้\n"
        "⚠️ เกินกำหนด — งาน/ภาษีที่เลยกำหนด\n"
        "👤 ลูกค้า <ชื่อ/รหัส> — ค้นหาลูกค้า\n"
        "❓ ช่วยเหลือ — เมนูนี้"
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
    income = db.query(func.sum(models.Transaction.amount)).filter(
        models.Transaction.month == m, models.Transaction.year == y,
        models.Transaction.transaction_type == "income").scalar() or 0

    return (
        f"📊 ภาพรวม ณ {_fmt_date(today)}\n"
        f"ประจำเดือน {MONTH_TH[m]} {y + 543}\n"
        "──────────────\n"
        f"👥 ลูกค้าทั้งหมด {total_clients} ราย (active {active_clients})\n"
        f"📋 งานเดือนนี้: เสร็จ {completed_jobs} / ค้าง {pending_jobs}\n"
        f"💰 ค้างชำระ {unpaid_invoices} ใบ ({_fmt_baht(unpaid_amount)} บาท)\n"
        f"📈 รายได้ลูกค้าเดือนนี้ {_fmt_baht(income)} บาท"
    )


def _cmd_pending_jobs(db: Session) -> str:
    today = date.today()
    jobs = db.query(models.MonthlyJob).filter(
        models.MonthlyJob.month == today.month,
        models.MonthlyJob.year == today.year,
        models.MonthlyJob.status != "completed",
    ).all()
    if not jobs:
        return f"✅ งานเดือน {MONTH_TH[today.month]} {today.year + 543} เสร็จครบแล้ว ไม่มีงานค้าง"

    lines = [f"📋 งานค้างเดือน {MONTH_TH[today.month]} {today.year + 543} ({len(jobs)} ราย)", "──────────────"]
    for j in jobs[:15]:
        name = j.client.name if j.client else f"#{j.client_id}"
        todo = []
        if not j.documents_received:
            todo.append("รับเอกสาร")
        if not j.bookkeeping_done:
            todo.append("ทำบัญชี")
        if not j.vat_filed:
            todo.append("ยื่น VAT")
        if not j.wht_filed:
            todo.append("ยื่นหัก ณ ที่จ่าย")
        if not j.sso_filed:
            todo.append("ประกันสังคม")
        step = " • ".join(todo) if todo else "ใกล้เสร็จ"
        lines.append(f"• {name}\n   ↳ {step}")
    if len(jobs) > 15:
        lines.append(f"...และอีก {len(jobs) - 15} ราย")
    return "\n".join(lines)


def _cmd_deadlines(db: Session) -> str:
    today = date.today()
    horizon = today + timedelta(days=30)
    filings = db.query(models.TaxFiling).filter(
        models.TaxFiling.status == "pending",
        models.TaxFiling.due_date >= today,
        models.TaxFiling.due_date <= horizon,
    ).order_by(models.TaxFiling.due_date).limit(20).all()
    if not filings:
        return "🧾 ไม่มีกำหนดยื่นภาษีใน 30 วันข้างหน้า"

    lines = ["🧾 กำหนดยื่นภาษี 30 วันข้างหน้า", "──────────────"]
    for f in filings:
        name = f.client.name if f.client else f"#{f.client_id}"
        days = (f.due_date - today).days if f.due_date else None
        urgent = "🔴" if days is not None and days <= 3 else "🟡" if days is not None and days <= 7 else "🟢"
        when = f"อีก {days} วัน" if days else "วันนี้"
        lines.append(f"{urgent} {_fmt_date(f.due_date)} ({when})\n   {f.filing_type} — {name}")
    return "\n".join(lines)


def _cmd_unpaid(db: Session) -> str:
    invoices = db.query(models.Invoice).filter(
        models.Invoice.status.in_(["sent", "overdue"])
    ).order_by(models.Invoice.due_date).limit(15).all()
    if not invoices:
        return "💰 ไม่มีใบแจ้งหนี้ค้างชำระ เยี่ยมมาก!"

    total = sum(inv.total or 0 for inv in invoices)
    lines = [f"💰 ใบแจ้งหนี้ค้างชำระ ({len(invoices)} ใบ)", f"ยอดรวม {_fmt_baht(total)} บาท", "──────────────"]
    for inv in invoices:
        name = inv.client.name if inv.client else f"#{inv.client_id}"
        tag = "⚠️ เกินกำหนด" if inv.status == "overdue" else "ครบกำหนด"
        lines.append(f"• {inv.invoice_number} — {name}\n   {_fmt_baht(inv.total)} บาท ({tag} {_fmt_date(inv.due_date)})")
    return "\n".join(lines)


def _cmd_today(db: Session) -> str:
    today = date.today()
    due_today = db.query(models.TaxFiling).filter(
        models.TaxFiling.status == "pending",
        models.TaxFiling.due_date == today,
    ).all()
    due_soon = db.query(func.count(models.TaxFiling.id)).filter(
        models.TaxFiling.status == "pending",
        models.TaxFiling.due_date > today,
        models.TaxFiling.due_date <= today + timedelta(days=3),
    ).scalar() or 0
    overdue_tax = db.query(func.count(models.TaxFiling.id)).filter(
        models.TaxFiling.status == "overdue").scalar() or 0
    overdue_inv = db.query(func.count(models.Invoice.id)).filter(
        models.Invoice.status == "overdue").scalar() or 0
    pending_jobs = db.query(func.count(models.MonthlyJob.id)).filter(
        models.MonthlyJob.month == today.month,
        models.MonthlyJob.year == today.year,
        models.MonthlyJob.status != "completed").scalar() or 0

    lines = [f"📅 สรุปงานวันนี้ {_fmt_date(today)}", "──────────────"]
    if due_today:
        lines.append(f"🔴 ต้องยื่นภาษีวันนี้ {len(due_today)} รายการ:")
        for f in due_today[:10]:
            name = f.client.name if f.client else f"#{f.client_id}"
            lines.append(f"   • {f.filing_type} — {name}")
    else:
        lines.append("✅ วันนี้ไม่มีกำหนดยื่นภาษี")
    lines.append("──────────────")
    lines.append(f"⏳ ใกล้ครบกำหนด (3 วัน): {due_soon} รายการ")
    lines.append(f"📋 งานเดือนนี้ค้าง: {pending_jobs} ราย")
    lines.append(f"⚠️ เกินกำหนด: ภาษี {overdue_tax} / ใบแจ้งหนี้ {overdue_inv}")
    return "\n".join(lines)


def _cmd_overdue(db: Session) -> str:
    today = date.today()
    tax = db.query(models.TaxFiling).filter(
        models.TaxFiling.status == "overdue"
    ).order_by(models.TaxFiling.due_date).limit(15).all()
    inv = db.query(models.Invoice).filter(
        models.Invoice.status == "overdue"
    ).order_by(models.Invoice.due_date).limit(15).all()
    if not tax and not inv:
        return "✅ ไม่มีรายการเกินกำหนด ทุกอย่างเรียบร้อย"

    lines = ["⚠️ รายการเกินกำหนด", "──────────────"]
    if tax:
        lines.append(f"🧾 ภาษีเกินกำหนด ({len(tax)}):")
        for f in tax:
            name = f.client.name if f.client else f"#{f.client_id}"
            lines.append(f"   • {f.filing_type} — {name} (กำหนด {_fmt_date(f.due_date)})")
    if inv:
        lines.append(f"💰 ใบแจ้งหนี้เกินกำหนด ({len(inv)}):")
        for i in inv:
            name = i.client.name if i.client else f"#{i.client_id}"
            lines.append(f"   • {i.invoice_number} — {name} ({_fmt_baht(i.total)} บาท)")
    return "\n".join(lines)


def _cmd_client(db: Session, keyword: str) -> str:
    keyword = (keyword or "").strip()
    if not keyword:
        total = db.query(func.count(models.Client.id)).filter(
            models.Client.status == "active").scalar() or 0
        return (
            f"👤 มีลูกค้า active {total} ราย\n"
            "ค้นหารายตัวด้วยการพิมพ์:\n"
            "   ลูกค้า <ชื่อหรือรหัส>\n"
            "เช่น: ลูกค้า AC001 หรือ ลูกค้า บริษัท"
        )

    like = f"%{keyword}%"
    clients = db.query(models.Client).filter(
        (models.Client.name.ilike(like)) |
        (models.Client.code.ilike(like)) |
        (models.Client.tax_id.ilike(like))
    ).limit(10).all()
    if not clients:
        return f"🔍 ไม่พบลูกค้าที่ตรงกับ \"{keyword}\""

    if len(clients) == 1:
        return _client_detail(db, clients[0])

    lines = [f"🔍 พบ {len(clients)} ราย — พิมพ์รหัสเพื่อดูรายละเอียด", "──────────────"]
    for c in clients:
        lines.append(f"• [{c.code or '-'}] {c.name}")
    return "\n".join(lines)


def _client_detail(db: Session, c: models.Client) -> str:
    today = date.today()
    job = db.query(models.MonthlyJob).filter(
        models.MonthlyJob.client_id == c.id,
        models.MonthlyJob.month == today.month,
        models.MonthlyJob.year == today.year,
    ).first()
    unpaid = db.query(func.sum(models.Invoice.total)).filter(
        models.Invoice.client_id == c.id,
        models.Invoice.status.in_(["sent", "overdue"]),
    ).scalar() or 0
    next_filing = db.query(models.TaxFiling).filter(
        models.TaxFiling.client_id == c.id,
        models.TaxFiling.status == "pending",
        models.TaxFiling.due_date >= today,
    ).order_by(models.TaxFiling.due_date).first()

    job_status = "ยังไม่เริ่ม"
    if job:
        job_status = {"completed": "เสร็จแล้ว", "in_progress": "กำลังทำ"}.get(job.status, "รอดำเนินการ")

    lines = [
        f"👤 {c.name}",
        f"รหัส {c.code or '-'} • {c.business_type or '-'}",
        "──────────────",
        f"เลขผู้เสียภาษี: {c.tax_id or '-'}",
        f"ผู้ติดต่อ: {c.contact_person or '-'} {('('+c.phone+')') if c.phone else ''}".strip(),
        f"VAT: {'จด' if c.vat_registered else 'ไม่จด'} • พนักงาน: {'มี' if c.has_employees else 'ไม่มี'}",
        f"ค่าบริการ/เดือน: {_fmt_baht(c.monthly_fee)} บาท",
        f"งานเดือนนี้: {job_status}",
        f"ค้างชำระ: {_fmt_baht(unpaid)} บาท",
    ]
    if next_filing:
        lines.append(f"ภาษีถัดไป: {next_filing.filing_type} ({_fmt_date(next_filing.due_date)})")
    return "\n".join(lines)


# ────────────────────────────────────────────────────────────────
# Command router
# ────────────────────────────────────────────────────────────────

def handle_text(text: str) -> dict:
    """
    รับข้อความ -> คืน dict {"text": ..., "quick": [...]}
    ใช้ได้ทั้ง webhook จริงและโหมดจำลองผ่านหน้าเว็บ
    """
    raw = (text or "").strip()
    low = raw.lower()
    db = SessionLocal()
    try:
        if low in ("help", "เมนู", "menu", "ช่วยเหลือ", "?", "/help", "start", "เริ่ม"):
            return {"text": _cmd_help(), "quick": MENU_ITEMS}
        if low in ("สรุป", "dashboard", "ภาพรวม", "summary"):
            return {"text": _cmd_dashboard(db), "quick": MENU_ITEMS}
        if low in ("งานค้าง", "งาน", "jobs", "งานรายเดือน"):
            return {"text": _cmd_pending_jobs(db), "quick": MENU_ITEMS}
        if low in ("ภาษี", "กำหนดยื่น", "deadline", "deadlines", "tax"):
            return {"text": _cmd_deadlines(db), "quick": MENU_ITEMS}
        if low in ("ค้างชำระ", "หนี้", "ใบแจ้งหนี้", "invoice", "invoices", "unpaid"):
            return {"text": _cmd_unpaid(db), "quick": MENU_ITEMS}
        if low in ("วันนี้", "today"):
            return {"text": _cmd_today(db), "quick": MENU_ITEMS}
        if low in ("เกินกำหนด", "overdue", "ค้าง"):
            return {"text": _cmd_overdue(db), "quick": MENU_ITEMS}
        if low == "ลูกค้า" or low in ("client", "clients", "ลูกค้าทั้งหมด"):
            return {"text": _cmd_client(db, ""), "quick": MENU_ITEMS}
        if low.startswith("ลูกค้า ") or low.startswith("client "):
            kw = raw.split(" ", 1)[1] if " " in raw else ""
            return {"text": _cmd_client(db, kw), "quick": MENU_ITEMS}

        # ค้นหาแบบอิสระ: ลองตีความเป็นรหัส/ชื่อ ลูกค้า
        guess = _cmd_client(db, raw)
        if not guess.startswith("🔍 ไม่พบ"):
            return {"text": guess, "quick": MENU_ITEMS}

        return {
            "text": f"ไม่เข้าใจคำสั่ง \"{raw}\" 🤔\nพิมพ์ \"ช่วยเหลือ\" เพื่อดูเมนูทั้งหมด",
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
        if etype == "follow":
            # ทักทายเมื่อมีคนเพิ่มเพื่อน
            if reply_token:
                reply_message(reply_token, [text_message(
                    "สวัสดีครับ 🙏 ผมคือบอทผู้ช่วยสำนักงานบัญชี\n" + _cmd_help(),
                    MENU_ITEMS,
                )])
            continue
        if etype == "message" and ev.get("message", {}).get("type") == "text":
            text = ev["message"].get("text", "")
            result = handle_text(text)
            if reply_token:
                reply_message(reply_token, build_reply_messages(result))


# ────────────────────────────────────────────────────────────────
# Daily summary push (เรียกจาก scheduler หรือกดเองได้)
# ────────────────────────────────────────────────────────────────

def build_daily_digest() -> str:
    db = SessionLocal()
    try:
        return "🌅 สรุปประจำวัน\n\n" + _cmd_today(db) + "\n\n" + _cmd_deadlines(db)
    finally:
        db.close()


def push_daily_digest(to: str = None) -> dict:
    db = SessionLocal()
    try:
        target = to or get_default_recipient(db)
        digest = build_daily_digest()
        if not target:
            return {"sent": False, "reason": "ยังไม่ได้ตั้งค่าผู้รับ (default_recipient)", "preview": digest}
        ok = push_message(target, [text_message(digest, MENU_ITEMS)])
        return {"sent": ok, "to": target, "preview": digest}
    finally:
        db.close()
