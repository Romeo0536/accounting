from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
import models
import schemas

router = APIRouter()


@router.get("/", response_model=List[schemas.AnnualJobResponse])
def list_annual_jobs(
    year: Optional[int] = None,
    client_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(models.AnnualJob)
    if year:
        q = q.filter(models.AnnualJob.year == year)
    if client_id:
        q = q.filter(models.AnnualJob.client_id == client_id)
    if status:
        q = q.filter(models.AnnualJob.status == status)
    return q.all()


@router.post("/", response_model=schemas.AnnualJobResponse, status_code=201)
def create_annual_job(data: schemas.AnnualJobCreate, db: Session = Depends(get_db)):
    existing = db.query(models.AnnualJob).filter(
        models.AnnualJob.client_id == data.client_id,
        models.AnnualJob.year == data.year,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="มีงานปีนี้แล้ว")
    job = models.AnnualJob(**data.model_dump())
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.post("/bulk-create", status_code=201)
def bulk_create_annual_jobs(year: int, db: Session = Depends(get_db)):
    clients = db.query(models.Client).filter(models.Client.status == "active").all()
    created = 0
    for c in clients:
        existing = db.query(models.AnnualJob).filter(
            models.AnnualJob.client_id == c.id,
            models.AnnualJob.year == year,
        ).first()
        if not existing:
            job = models.AnnualJob(client_id=c.id, year=year, audit_required=(c.business_type == "บริษัทจำกัด"))
            db.add(job)
            created += 1
    db.commit()
    return {"created": created, "year": year}


@router.get("/{job_id}", response_model=schemas.AnnualJobResponse)
def get_annual_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(models.AnnualJob).filter(models.AnnualJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="ไม่พบงาน")
    return job


@router.put("/{job_id}", response_model=schemas.AnnualJobResponse)
def update_annual_job(job_id: int, data: schemas.AnnualJobUpdate, db: Session = Depends(get_db)):
    job = db.query(models.AnnualJob).filter(models.AnnualJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="ไม่พบงาน")
    from datetime import date
    update_data = data.model_dump(exclude_none=True)
    today = date.today()
    if update_data.get("annual_fs_done") and not job.annual_fs_done_date:
        update_data.setdefault("annual_fs_done_date", today)
    if update_data.get("pnd51_filed") and not job.pnd51_filed_date:
        update_data.setdefault("pnd51_filed_date", today)
    if update_data.get("pnd50_filed") and not job.pnd50_filed_date:
        update_data.setdefault("pnd50_filed_date", today)
    if update_data.get("boj5_filed") and not job.boj5_filed_date:
        update_data.setdefault("boj5_filed_date", today)
    if update_data.get("audit_done") and not job.audit_done_date:
        update_data.setdefault("audit_done_date", today)
    for k, v in update_data.items():
        setattr(job, k, v)
    steps = [job.annual_fs_done, job.pnd50_filed, job.boj5_filed]
    if all(steps):
        job.status = "completed"
    elif any(steps) or job.pnd51_filed:
        job.status = "in_progress"
    db.commit()
    db.refresh(job)
    return job


@router.delete("/{job_id}", status_code=204)
def delete_annual_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(models.AnnualJob).filter(models.AnnualJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="ไม่พบงาน")
    db.delete(job)
    db.commit()
