from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date
from database import get_db
import models

router = APIRouter()


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    today = date.today()
    month, year = today.month, today.year

    total_clients = db.query(func.count(models.Client.id)).scalar()
    active_clients = db.query(func.count(models.Client.id)).filter(models.Client.status == "active").scalar()

    pending_jobs = db.query(func.count(models.MonthlyJob.id)).filter(
        models.MonthlyJob.month == month,
        models.MonthlyJob.year == year,
        models.MonthlyJob.status != "completed",
    ).scalar()

    completed_jobs = db.query(func.count(models.MonthlyJob.id)).filter(
        models.MonthlyJob.month == month,
        models.MonthlyJob.year == year,
        models.MonthlyJob.status == "completed",
    ).scalar()

    unpaid_invoices = db.query(func.count(models.Invoice.id)).filter(
        models.Invoice.status.in_(["sent", "overdue"])
    ).scalar()

    unpaid_amount = db.query(func.sum(models.Invoice.total)).filter(
        models.Invoice.status.in_(["sent", "overdue"])
    ).scalar() or 0

    income_this_month = db.query(func.sum(models.Transaction.amount)).filter(
        models.Transaction.month == month,
        models.Transaction.year == year,
        models.Transaction.transaction_type == "income",
    ).scalar() or 0

    return {
        "total_clients": total_clients,
        "active_clients": active_clients,
        "pending_monthly_jobs": pending_jobs,
        "completed_monthly_jobs": completed_jobs,
        "unpaid_invoices": unpaid_invoices,
        "unpaid_amount": unpaid_amount,
        "this_month_income": income_this_month,
        "current_month": month,
        "current_year": year,
    }


@router.get("/pending-jobs")
def get_pending_jobs(db: Session = Depends(get_db)):
    today = date.today()
    jobs = db.query(models.MonthlyJob).filter(
        models.MonthlyJob.month == today.month,
        models.MonthlyJob.year == today.year,
        models.MonthlyJob.status != "completed",
    ).all()
    return [
        {
            "id": j.id,
            "client_id": j.client_id,
            "client_name": j.client.name if j.client else "",
            "client_code": j.client.code if j.client else "",
            "month": j.month,
            "year": j.year,
            "status": j.status,
            "documents_received": j.documents_received,
            "bookkeeping_done": j.bookkeeping_done,
            "vat_filed": j.vat_filed,
            "wht_filed": j.wht_filed,
            "sso_filed": j.sso_filed,
            "financial_statement_done": j.financial_statement_done,
        }
        for j in jobs
    ]


@router.get("/upcoming-deadlines")
def get_upcoming_deadlines(db: Session = Depends(get_db)):
    """ภาษีที่ต้องยื่นเร็วๆ นี้"""
    today = date.today()
    filings = db.query(models.TaxFiling).filter(
        models.TaxFiling.status == "pending",
        models.TaxFiling.due_date >= today,
    ).order_by(models.TaxFiling.due_date).limit(20).all()
    return [
        {
            "id": f.id,
            "client_name": f.client.name if f.client else "",
            "client_code": f.client.code if f.client else "",
            "filing_type": f.filing_type,
            "month": f.month,
            "year": f.year,
            "due_date": f.due_date.isoformat() if f.due_date else None,
        }
        for f in filings
    ]


@router.get("/unpaid-invoices")
def get_unpaid_invoices(db: Session = Depends(get_db)):
    invoices = db.query(models.Invoice).filter(
        models.Invoice.status.in_(["sent", "overdue"])
    ).order_by(models.Invoice.due_date).limit(10).all()
    return [
        {
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "client_name": inv.client.name if inv.client else "",
            "total": inv.total,
            "due_date": inv.due_date.isoformat() if inv.due_date else None,
            "status": inv.status,
        }
        for inv in invoices
    ]
