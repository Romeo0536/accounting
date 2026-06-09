from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from database import get_db
import models
import schemas

router = APIRouter()


@router.get("/", response_model=List[schemas.WHTRecordResponse])
def list_wht_records(
    client_id: Optional[int] = None,
    month: Optional[int] = None,
    year: Optional[int] = None,
    wht_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(models.WHTRecord)
    if client_id:
        q = q.filter(models.WHTRecord.client_id == client_id)
    if month:
        q = q.filter(models.WHTRecord.month == month)
    if year:
        q = q.filter(models.WHTRecord.year == year)
    if wht_type:
        q = q.filter(models.WHTRecord.wht_type == wht_type)
    return q.order_by(models.WHTRecord.date.desc()).all()


@router.post("/", response_model=schemas.WHTRecordResponse, status_code=201)
def create_wht_record(data: schemas.WHTRecordCreate, db: Session = Depends(get_db)):
    rec_data = data.model_dump()
    if not rec_data.get("month"):
        rec_data["month"] = data.date.month
    if not rec_data.get("year"):
        rec_data["year"] = data.date.year
    rec = models.WHTRecord(**rec_data)
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


@router.get("/summary", response_model=dict)
def get_wht_summary(client_id: int, month: int, year: int, db: Session = Depends(get_db)):
    """สรุปภาษีหัก ณ ที่จ่ายรายเดือน"""
    rows = db.query(
        models.WHTRecord.wht_type,
        models.WHTRecord.direction,
        func.sum(models.WHTRecord.income_amount).label("total_income"),
        func.sum(models.WHTRecord.wht_amount).label("total_wht"),
    ).filter(
        models.WHTRecord.client_id == client_id,
        models.WHTRecord.month == month,
        models.WHTRecord.year == year,
    ).group_by(
        models.WHTRecord.wht_type,
        models.WHTRecord.direction,
    ).all()

    result = {}
    for wht_type, direction, total_income, total_wht in rows:
        key = f"{wht_type}_{direction}"
        result[key] = {
            "wht_type": wht_type,
            "direction": direction,
            "total_income": total_income or 0,
            "total_wht": total_wht or 0,
        }
    return {"client_id": client_id, "month": month, "year": year, "records": result}


@router.get("/{record_id}", response_model=schemas.WHTRecordResponse)
def get_wht_record(record_id: int, db: Session = Depends(get_db)):
    rec = db.query(models.WHTRecord).filter(models.WHTRecord.id == record_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="ไม่พบรายการ")
    return rec


@router.put("/{record_id}", response_model=schemas.WHTRecordResponse)
def update_wht_record(record_id: int, data: schemas.WHTRecordUpdate, db: Session = Depends(get_db)):
    rec = db.query(models.WHTRecord).filter(models.WHTRecord.id == record_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="ไม่พบรายการ")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(rec, k, v)
    db.commit()
    db.refresh(rec)
    return rec


@router.delete("/{record_id}", status_code=204)
def delete_wht_record(record_id: int, db: Session = Depends(get_db)):
    rec = db.query(models.WHTRecord).filter(models.WHTRecord.id == record_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="ไม่พบรายการ")
    db.delete(rec)
    db.commit()
