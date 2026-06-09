from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from database import get_db
import models
import schemas

router = APIRouter()


def compute_status(job: models.MonthlyJob) -> str:
    steps = [job.documents_received, job.bookkeeping_done, job.financial_statement_done]
    if all(steps):
        return "completed"
    if any(steps) or job.vat_filed or job.wht_filed or job.sso_filed:
        return "in_progress"
    return "pending"


@router.get("/", response_model=List[schemas.MonthlyJobResponse])
def list_monthly_jobs(
    month: Optional[int] = None,
    year: Optional[int] = None,
    client_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(models.MonthlyJob)
    if month:
        q = q.filter(models.MonthlyJob.month == month)
    if year:
        q = q.filter(models.MonthlyJob.year == year)
    if client_id:
        q = q.filter(models.MonthlyJob.client_id == client_id)
    if status:
        q = q.filter(models.MonthlyJob.status == status)
    return q.all()


@router.post("/", response_model=schemas.MonthlyJobResponse, status_code=201)
def create_monthly_job(data: schemas.MonthlyJobCreate, db: Session = Depends(get_db)):
    existing = db.query(models.MonthlyJob).filter(
        models.MonthlyJob.client_id == data.client_id,
        models.MonthlyJob.month == data.month,
        models.MonthlyJob.year == data.year,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="มีงานเดือนนี้แล้ว")
    job = models.MonthlyJob(**data.model_dump())
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.post("/bulk-create", status_code=201)
def bulk_create_monthly_jobs(month: int, year: int, db: Session = Depends(get_db)):
    """สร้างงานรายเดือนสำหรับลูกค้า active ทุกราย"""
    clients = db.query(models.Client).filter(models.Client.status == "active").all()
    created = 0
    for c in clients:
        existing = db.query(models.MonthlyJob).filter(
            models.MonthlyJob.client_id == c.id,
            models.MonthlyJob.month == month,
            models.MonthlyJob.year == year,
        ).first()
        if not existing:
            job = models.MonthlyJob(client_id=c.id, month=month, year=year)
            db.add(job)
            created += 1
    db.commit()
    return {"created": created, "month": month, "year": year}


@router.get("/{job_id}", response_model=schemas.MonthlyJobResponse)
def get_monthly_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(models.MonthlyJob).filter(models.MonthlyJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="ไม่พบงาน")
    return job


@router.put("/{job_id}", response_model=schemas.MonthlyJobResponse)
def update_monthly_job(job_id: int, data: schemas.MonthlyJobUpdate, db: Session = Depends(get_db)):
    job = db.query(models.MonthlyJob).filter(models.MonthlyJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="ไม่พบงาน")
    update_data = data.model_dump(exclude_none=True)
    # Auto-set dates when step is checked
    today = date.today()
    if update_data.get("documents_received") and not job.documents_received_date:
        update_data.setdefault("documents_received_date", today)
    if update_data.get("bookkeeping_done") and not job.bookkeeping_done_date:
        update_data.setdefault("bookkeeping_done_date", today)
    if update_data.get("vat_filed") and not job.vat_filed_date:
        update_data.setdefault("vat_filed_date", today)
    if update_data.get("wht_filed") and not job.wht_filed_date:
        update_data.setdefault("wht_filed_date", today)
    if update_data.get("sso_filed") and not job.sso_filed_date:
        update_data.setdefault("sso_filed_date", today)
    if update_data.get("financial_statement_done") and not job.financial_statement_done_date:
        update_data.setdefault("financial_statement_done_date", today)
    for k, v in update_data.items():
        setattr(job, k, v)
    # Auto-compute status
    job.status = compute_status(job)
    db.commit()
    db.refresh(job)
    return job


@router.delete("/{job_id}", status_code=204)
def delete_monthly_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(models.MonthlyJob).filter(models.MonthlyJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="ไม่พบงาน")
    db.delete(job)
    db.commit()
