from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from database import get_db
import models
import schemas

router = APIRouter()


@router.get("/", response_model=List[schemas.TransactionResponse])
def list_transactions(
    client_id: Optional[int] = None,
    month: Optional[int] = None,
    year: Optional[int] = None,
    transaction_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(models.Transaction)
    if client_id:
        q = q.filter(models.Transaction.client_id == client_id)
    if month:
        q = q.filter(models.Transaction.month == month)
    if year:
        q = q.filter(models.Transaction.year == year)
    if transaction_type:
        q = q.filter(models.Transaction.transaction_type == transaction_type)
    return q.order_by(models.Transaction.date.desc()).all()


@router.post("/", response_model=schemas.TransactionResponse, status_code=201)
def create_transaction(data: schemas.TransactionCreate, db: Session = Depends(get_db)):
    tx_data = data.model_dump()
    if not tx_data.get("month"):
        tx_data["month"] = data.date.month
    if not tx_data.get("year"):
        tx_data["year"] = data.date.year
    tx = models.Transaction(**tx_data)
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


@router.get("/summary", response_model=dict)
def get_summary(
    client_id: int,
    month: int,
    year: int,
    db: Session = Depends(get_db),
):
    """สรุปรายรับ-รายจ่าย และ VAT รายเดือน"""
    income = db.query(
        func.sum(models.Transaction.amount),
        func.sum(models.Transaction.vat_amount),
    ).filter(
        models.Transaction.client_id == client_id,
        models.Transaction.month == month,
        models.Transaction.year == year,
        models.Transaction.transaction_type == "income",
    ).first()

    expense = db.query(
        func.sum(models.Transaction.amount),
        func.sum(models.Transaction.vat_amount),
    ).filter(
        models.Transaction.client_id == client_id,
        models.Transaction.month == month,
        models.Transaction.year == year,
        models.Transaction.transaction_type == "expense",
    ).first()

    income_amount = income[0] or 0
    income_vat = income[1] or 0
    expense_amount = expense[0] or 0
    expense_vat = expense[1] or 0

    return {
        "client_id": client_id,
        "month": month,
        "year": year,
        "income_amount": income_amount,
        "income_vat": income_vat,  # ภาษีขาย
        "expense_amount": expense_amount,
        "expense_vat": expense_vat,  # ภาษีซื้อ
        "net_vat": income_vat - expense_vat,  # VAT ที่ต้องชำระ
        "profit": income_amount - expense_amount,
    }


@router.get("/annual-summary", response_model=dict)
def get_annual_summary(client_id: int, year: int, db: Session = Depends(get_db)):
    """สรุปรายปี สำหรับ P&L"""
    rows = db.query(
        models.Transaction.month,
        models.Transaction.transaction_type,
        func.sum(models.Transaction.amount).label("total"),
    ).filter(
        models.Transaction.client_id == client_id,
        models.Transaction.year == year,
    ).group_by(
        models.Transaction.month,
        models.Transaction.transaction_type,
    ).all()

    monthly = {}
    for month, tx_type, total in rows:
        if month not in monthly:
            monthly[month] = {"income": 0, "expense": 0}
        monthly[month][tx_type] = total

    total_income = sum(v["income"] for v in monthly.values())
    total_expense = sum(v["expense"] for v in monthly.values())

    return {
        "client_id": client_id,
        "year": year,
        "monthly": monthly,
        "total_income": total_income,
        "total_expense": total_expense,
        "net_profit": total_income - total_expense,
    }


@router.get("/{tx_id}", response_model=schemas.TransactionResponse)
def get_transaction(tx_id: int, db: Session = Depends(get_db)):
    tx = db.query(models.Transaction).filter(models.Transaction.id == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="ไม่พบรายการ")
    return tx


@router.put("/{tx_id}", response_model=schemas.TransactionResponse)
def update_transaction(tx_id: int, data: schemas.TransactionUpdate, db: Session = Depends(get_db)):
    tx = db.query(models.Transaction).filter(models.Transaction.id == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="ไม่พบรายการ")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(tx, k, v)
    db.commit()
    db.refresh(tx)
    return tx


@router.delete("/{tx_id}", status_code=204)
def delete_transaction(tx_id: int, db: Session = Depends(get_db)):
    tx = db.query(models.Transaction).filter(models.Transaction.id == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="ไม่พบรายการ")
    db.delete(tx)
    db.commit()
