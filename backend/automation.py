"""
ระบบ Automation - งานที่รันอัตโนมัติตามกำหนดเวลา
"""
import json
from datetime import date, timedelta
from calendar import monthrange
from sqlalchemy.orm import Session
from database import SessionLocal
import models


def get_db() -> Session:
    return SessionLocal()


def log(db: Session, task_name: str, status: str, message: str,
        details: dict = None, trigger: str = "auto"):
    entry = models.AutomationLog(
        task_name=task_name,
        trigger=trigger,
        status=status,
        message=message,
        details=json.dumps(details or {}, ensure_ascii=False),
    )
    db.add(entry)
    db.commit()


# ────────────────────────────────────────────────────────────────
# คำนวณกำหนดยื่นภาษี
# ────────────────────────────────────────────────────────────────

def _next_month(month: int, year: int):
    """คืน (เดือน, ปี) ของเดือนถัดไป"""
    if month == 12:
        return 1, year + 1
    return month + 1, year


def _due_date(day: int, month: int, year: int) -> date:
    """ถ้าวันที่ตกวันหยุด ให้เป็นวันทำการถัดไป (อย่างง่าย)"""
    d = date(year, month, day)
    while d.weekday() >= 5:   # เสาร์=5, อาทิตย์=6
        d += timedelta(days=1)
    return d


def tax_due_dates(period_month: int, period_year: int, client: models.Client) -> list[dict]:
    """
    คืนรายการภาษีที่ต้องยื่นสำหรับลูกค้า ตามเงื่อนไขของกิจการ
    period = เดือนที่ต้องรายงาน (ยื่นแบบในเดือนถัดไป)
    """
    nm, ny = _next_month(period_month, period_year)
    filings = []

    if client.vat_registered:
        filings.append({
            "filing_type": "ภพ.30",
            "due_date": _due_date(15, nm, ny),
        })

    if client.has_employees:
        filings.append({
            "filing_type": "ภงด.1",
            "due_date": _due_date(7, nm, ny),
        })
        filings.append({
            "filing_type": "ประกันสังคม",
            "due_date": _due_date(15, nm, ny),
        })

    # ภงด.3 / ภงด.53 - บริการทั่วไป (เพิ่มเสมอ)
    filings.append({
        "filing_type": "ภงด.3",
        "due_date": _due_date(7, nm, ny),
    })
    if client.business_type in ("บริษัทจำกัด", "ห้างหุ้นส่วนจำกัด"):
        filings.append({
            "filing_type": "ภงด.53",
            "due_date": _due_date(7, nm, ny),
        })

    return filings


# ────────────────────────────────────────────────────────────────
# Task 1: สร้างงานรายเดือนสำหรับลูกค้าทุกราย
# ────────────────────────────────────────────────────────────────

def auto_create_monthly_jobs(month: int = None, year: int = None,
                             trigger: str = "auto") -> dict:
    db = get_db()
    try:
        today = date.today()
        m = month or today.month
        y = year or today.year

        clients = db.query(models.Client).filter(models.Client.status == "active").all()
        created, skipped = 0, 0
        for c in clients:
            exists = db.query(models.MonthlyJob).filter(
                models.MonthlyJob.client_id == c.id,
                models.MonthlyJob.month == m,
                models.MonthlyJob.year == y,
            ).first()
            if not exists:
                db.add(models.MonthlyJob(client_id=c.id, month=m, year=y))
                created += 1
            else:
                skipped += 1

        db.commit()
        result = {"created": created, "skipped": skipped, "month": m, "year": y}
        log(db, "สร้างงานรายเดือน", "success",
            f"สร้างงาน {created} ราย (ข้าม {skipped} ราย) เดือน {m}/{y}", result, trigger)
        return result
    except Exception as e:
        log(db, "สร้างงานรายเดือน", "error", str(e), {}, trigger)
        raise
    finally:
        db.close()


# ────────────────────────────────────────────────────────────────
# Task 2: สร้างรายการภาษีพร้อมกำหนดวัน
# ────────────────────────────────────────────────────────────────

def auto_generate_tax_deadlines(month: int = None, year: int = None,
                                trigger: str = "auto") -> dict:
    db = get_db()
    try:
        today = date.today()
        m = month or today.month
        y = year or today.year

        clients = db.query(models.Client).filter(models.Client.status == "active").all()
        created, skipped = 0, 0
        for c in clients:
            for filing in tax_due_dates(m, y, c):
                exists = db.query(models.TaxFiling).filter(
                    models.TaxFiling.client_id == c.id,
                    models.TaxFiling.filing_type == filing["filing_type"],
                    models.TaxFiling.month == m,
                    models.TaxFiling.year == y,
                ).first()
                if not exists:
                    db.add(models.TaxFiling(
                        client_id=c.id,
                        filing_type=filing["filing_type"],
                        month=m,
                        year=y,
                        due_date=filing["due_date"],
                        status="pending",
                    ))
                    created += 1
                else:
                    skipped += 1

        db.commit()
        result = {"created": created, "skipped": skipped, "month": m, "year": y}
        log(db, "สร้างรายการภาษี", "success",
            f"สร้างรายการภาษี {created} รายการ (ข้าม {skipped}) เดือน {m}/{y}", result, trigger)
        return result
    except Exception as e:
        log(db, "สร้างรายการภาษี", "error", str(e), {}, trigger)
        raise
    finally:
        db.close()


# ────────────────────────────────────────────────────────────────
# Task 3: ออกใบแจ้งหนี้รายเดือนอัตโนมัติ
# ────────────────────────────────────────────────────────────────

def auto_generate_invoices(month: int = None, year: int = None,
                           trigger: str = "auto") -> dict:
    db = get_db()
    try:
        today = date.today()
        m = month or today.month
        y = year or today.year

        # กำหนดครบชำระ = วันสุดท้ายของเดือน
        last_day = monthrange(y, m)[1]
        due_date = date(y, m, last_day)

        clients = db.query(models.Client).filter(
            models.Client.status == "active",
            models.Client.monthly_fee > 0,
        ).all()

        created, skipped = 0, 0
        for c in clients:
            exists = db.query(models.Invoice).filter(
                models.Invoice.client_id == c.id,
                models.Invoice.service_month == m,
                models.Invoice.service_year == y,
            ).first()
            if not exists:
                # สร้างเลขที่ใบแจ้งหนี้
                count = db.query(models.Invoice).filter(
                    models.Invoice.invoice_number.like(f"INV-{y}-%")
                ).count()
                inv_num = f"INV-{y}-{count + 1:04d}"

                subtotal = c.monthly_fee
                vat = round(subtotal * 7 / 100, 2) if c.vat_registered else 0
                total = subtotal + vat

                invoice = models.Invoice(
                    invoice_number=inv_num,
                    client_id=c.id,
                    invoice_date=today,
                    due_date=due_date,
                    service_month=m,
                    service_year=y,
                    subtotal=subtotal,
                    vat_amount=vat,
                    total=total,
                    status="sent",
                )
                db.add(invoice)
                db.flush()
                db.add(models.InvoiceItem(
                    invoice_id=invoice.id,
                    description=f"ค่าบริการบัญชีประจำเดือน {m}/{y}",
                    quantity=1,
                    unit_price=subtotal,
                    amount=subtotal,
                ))
                created += 1
            else:
                skipped += 1

        db.commit()
        result = {"created": created, "skipped": skipped, "month": m, "year": y}
        log(db, "ออกใบแจ้งหนี้รายเดือน", "success",
            f"ออกใบแจ้งหนี้ {created} ใบ (ข้าม {skipped}) เดือน {m}/{y}", result, trigger)
        return result
    except Exception as e:
        log(db, "ออกใบแจ้งหนี้รายเดือน", "error", str(e), {}, trigger)
        raise
    finally:
        db.close()


# ────────────────────────────────────────────────────────────────
# Task 4: ตรวจสอบและ mark overdue
# ────────────────────────────────────────────────────────────────

def auto_mark_overdue(trigger: str = "auto") -> dict:
    db = get_db()
    try:
        today = date.today()
        tax_updated, inv_updated = 0, 0

        # ภาษีเกินกำหนด
        overdue_tax = db.query(models.TaxFiling).filter(
            models.TaxFiling.status == "pending",
            models.TaxFiling.due_date < today,
        ).all()
        for f in overdue_tax:
            f.status = "overdue"
            tax_updated += 1

        # ใบแจ้งหนี้เกินกำหนด
        overdue_inv = db.query(models.Invoice).filter(
            models.Invoice.status == "sent",
            models.Invoice.due_date < today,
        ).all()
        for inv in overdue_inv:
            inv.status = "overdue"
            inv_updated += 1

        db.commit()
        result = {"tax_overdue": tax_updated, "invoice_overdue": inv_updated}
        log(db, "ตรวจสอบ Overdue", "success",
            f"ภาษีเกินกำหนด {tax_updated} รายการ, ใบแจ้งหนี้ {inv_updated} ใบ", result, trigger)
        return result
    except Exception as e:
        log(db, "ตรวจสอบ Overdue", "error", str(e), {}, trigger)
        raise
    finally:
        db.close()


# ────────────────────────────────────────────────────────────────
# Task 5: Monthly Complete Setup (รวม task 1-3)
# ────────────────────────────────────────────────────────────────

def auto_monthly_setup(month: int = None, year: int = None,
                       trigger: str = "auto") -> dict:
    db = get_db()
    today = date.today()
    m = month or today.month
    y = year or today.year

    try:
        r1 = auto_create_monthly_jobs(m, y, trigger)
        r2 = auto_generate_tax_deadlines(m, y, trigger)
        r3 = auto_generate_invoices(m, y, trigger)
        result = {"jobs": r1, "tax_deadlines": r2, "invoices": r3}
        log(db, "ตั้งต้นเดือนครบชุด", "success",
            f"เดือน {m}/{y}: งาน={r1['created']} ภาษี={r2['created']} ใบแจ้งหนี้={r3['created']}", result, trigger)
        return result
    except Exception as e:
        log(db, "ตั้งต้นเดือนครบชุด", "error", str(e), {}, trigger)
        raise
    finally:
        db.close()


# ────────────────────────────────────────────────────────────────
# Task 6: Client Onboarding Automation
# ────────────────────────────────────────────────────────────────

def auto_onboard_client(client_id: int) -> dict:
    """เรียกหลังจากเพิ่มลูกค้าใหม่"""
    db = get_db()
    try:
        today = date.today()
        m, y = today.month, today.year
        client = db.query(models.Client).filter(models.Client.id == client_id).first()
        if not client:
            return {}

        # สร้างงานเดือนปัจจุบัน
        exists = db.query(models.MonthlyJob).filter(
            models.MonthlyJob.client_id == client_id,
            models.MonthlyJob.month == m,
            models.MonthlyJob.year == y,
        ).first()
        if not exists:
            db.add(models.MonthlyJob(client_id=client_id, month=m, year=y))

        # สร้างรายการภาษีเดือนปัจจุบัน
        for filing in tax_due_dates(m, y, client):
            exists = db.query(models.TaxFiling).filter(
                models.TaxFiling.client_id == client_id,
                models.TaxFiling.filing_type == filing["filing_type"],
                models.TaxFiling.month == m,
                models.TaxFiling.year == y,
            ).first()
            if not exists:
                db.add(models.TaxFiling(
                    client_id=client_id,
                    filing_type=filing["filing_type"],
                    month=m,
                    year=y,
                    due_date=filing["due_date"],
                    status="pending",
                ))

        db.commit()
        result = {"client_id": client_id, "client_name": client.name}
        log(db, "เพิ่มลูกค้าใหม่ (Auto Setup)", "success",
            f"ตั้งต้นงานสำหรับ {client.name} เดือน {m}/{y}", result, "auto")
        return result
    except Exception as e:
        log(db, "เพิ่มลูกค้าใหม่ (Auto Setup)", "error", str(e), {}, "auto")
        return {}
    finally:
        db.close()
