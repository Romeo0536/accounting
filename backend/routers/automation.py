from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import date
from database import get_db
import models
import automation as auto_tasks

router = APIRouter()


class AutomationLogResponse(BaseModel):
    id: int
    task_name: str
    trigger: str
    status: str
    message: Optional[str]
    details: Optional[str]
    created_at: Optional[date]

    model_config = {"from_attributes": True}


# ────────────────────────────────────────────────────────────────
# Logs
# ────────────────────────────────────────────────────────────────

@router.get("/logs")
def get_logs(limit: int = 50, db: Session = Depends(get_db)):
    logs = db.query(models.AutomationLog)\
        .order_by(models.AutomationLog.created_at.desc())\
        .limit(limit).all()
    return [
        {
            "id": l.id,
            "task_name": l.task_name,
            "trigger": l.trigger,
            "status": l.status,
            "message": l.message,
            "details": l.details,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in logs
    ]


# ────────────────────────────────────────────────────────────────
# Schedule info
# ────────────────────────────────────────────────────────────────

@router.get("/schedule")
def get_schedule():
    """แสดงตารางงาน automation ที่ตั้งไว้"""
    return [
        {
            "id": "daily_overdue_check",
            "name": "ตรวจสอบ Overdue",
            "description": "ตรวจสอบภาษีและใบแจ้งหนี้ที่เกินกำหนด และอัพเดตสถานะเป็น overdue",
            "schedule": "ทุกวัน เวลา 08:00 น.",
            "cron": "0 8 * * *",
        },
        {
            "id": "monthly_setup",
            "name": "ตั้งต้นเดือนใหม่",
            "description": "สร้างงานรายเดือน + รายการภาษีพร้อมกำหนดยื่น + ใบแจ้งหนี้ค่าบริการ สำหรับลูกค้าทุกราย",
            "schedule": "วันที่ 1 ของทุกเดือน เวลา 06:00 น.",
            "cron": "0 6 1 * *",
        },
        {
            "id": "client_onboard",
            "name": "ต้อนรับลูกค้าใหม่",
            "description": "เมื่อเพิ่มลูกค้าใหม่ ระบบจะสร้างงานเดือนปัจจุบัน + รายการภาษีที่เกี่ยวข้องให้อัตโนมัติ",
            "schedule": "ทันทีเมื่อเพิ่มลูกค้า",
            "cron": "event-driven",
        },
    ]


# ────────────────────────────────────────────────────────────────
# Manual triggers
# ────────────────────────────────────────────────────────────────

@router.post("/run/monthly-jobs")
def trigger_monthly_jobs(
    month: int = Query(default=date.today().month),
    year: int = Query(default=date.today().year),
):
    """สร้างงานรายเดือนสำหรับลูกค้าทุกราย (กดเองได้)"""
    try:
        result = auto_tasks.auto_create_monthly_jobs(month, year, trigger="manual")
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run/tax-deadlines")
def trigger_tax_deadlines(
    month: int = Query(default=date.today().month),
    year: int = Query(default=date.today().year),
):
    """สร้างรายการภาษีพร้อมกำหนดวัน (กดเองได้)"""
    try:
        result = auto_tasks.auto_generate_tax_deadlines(month, year, trigger="manual")
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run/invoices")
def trigger_invoices(
    month: int = Query(default=date.today().month),
    year: int = Query(default=date.today().year),
):
    """ออกใบแจ้งหนี้ค่าบริการรายเดือนอัตโนมัติ (กดเองได้)"""
    try:
        result = auto_tasks.auto_generate_invoices(month, year, trigger="manual")
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run/mark-overdue")
def trigger_mark_overdue():
    """ตรวจสอบและ mark overdue (กดเองได้)"""
    try:
        result = auto_tasks.auto_mark_overdue(trigger="manual")
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run/monthly-setup")
def trigger_monthly_setup(
    month: int = Query(default=date.today().month),
    year: int = Query(default=date.today().year),
):
    """รันทุกอย่างพร้อมกัน: งาน + ภาษี + ใบแจ้งหนี้"""
    try:
        result = auto_tasks.auto_monthly_setup(month, year, trigger="manual")
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
