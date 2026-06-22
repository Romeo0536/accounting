"""
Expense Tracking Router — บันทึก/ดูรายการค่าใช้จ่าย จากสลิป
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta
from sqlalchemy import func
from database import get_db
import models

router = APIRouter()


@router.get("/")
def list_expenses(
    days: int = Query(30, description="ย้อนหลัง N วัน"),
    category: str = Query(None, description="กรองหมวดหมู่"),
    db: Session = Depends(get_db),
):
    """ดูรายการค่าใช้จ่าย"""
    since = date.today() - timedelta(days=days)
    q = db.query(models.Expense).filter(models.Expense.created_at >= since)
    if category:
        q = q.filter(models.Expense.category == category)
    expenses = q.order_by(models.Expense.created_at.desc()).all()

    total = sum(e.amount or 0 for e in expenses)
    return {
        "expenses": [
            {
                "id": e.id,
                "merchant_name": e.merchant_name,
                "amount": e.amount,
                "category": e.category,
                "receipt_date": e.receipt_date.isoformat() if e.receipt_date else None,
                "receipt_time": e.receipt_time,
                "verified": e.verified,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in expenses
        ],
        "total": total,
        "count": len(expenses),
        "period_days": days,
    }


@router.get("/summary")
def get_summary(days: int = Query(30), db: Session = Depends(get_db)):
    """สรุปรายการค่าใช้จ่ายตามหมวดหมู่"""
    since = date.today() - timedelta(days=days)
    expenses = db.query(models.Expense).filter(
        models.Expense.created_at >= since
    ).all()

    by_category = {}
    for e in expenses:
        cat = e.category or "อื่น"
        if cat not in by_category:
            by_category[cat] = {"count": 0, "total": 0}
        by_category[cat]["count"] += 1
        by_category[cat]["total"] += e.amount or 0

    total_all = sum(e.amount or 0 for e in expenses)
    return {
        "by_category": by_category,
        "total": total_all,
        "count": len(expenses),
    }


@router.get("/unverified")
def get_unverified(db: Session = Depends(get_db)):
    """รายการที่ยังไม่ได้ยืนยัน (รอตรวจสอบ)"""
    expenses = db.query(models.Expense).filter(
        models.Expense.verified == False
    ).order_by(models.Expense.created_at.desc()).all()

    return [
        {
            "id": e.id,
            "merchant_name": e.merchant_name,
            "amount": e.amount,
            "category": e.category,
            "notes": e.notes,
            "ocr_confidence": e.ocr_confidence,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in expenses
    ]


@router.post("/{expense_id}/verify")
def verify_expense(
    expense_id: int,
    amount: float = None,
    category: str = None,
    notes: str = None,
    db: Session = Depends(get_db),
):
    """ยืนยันข้อมูลค่าใช้จ่าย (และแก้ไขถ้าต้อง)"""
    e = db.query(models.Expense).filter(models.Expense.id == expense_id).first()
    if not e:
        return {"error": "ไม่พบรายการ"}

    if amount is not None:
        e.amount = amount
    if category:
        e.category = category
    if notes:
        e.notes = notes
    e.verified = True
    e.updated_at = datetime.now()
    db.commit()
    return {"ok": True, "id": e.id}


@router.post("/{expense_id}/reject")
def reject_expense(expense_id: int, db: Session = Depends(get_db)):
    """ลบรายการ (ยกเลิก)"""
    e = db.query(models.Expense).filter(models.Expense.id == expense_id).first()
    if not e:
        return {"error": "ไม่พบรายการ"}
    db.delete(e)
    db.commit()
    return {"ok": True}
