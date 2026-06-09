from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
import models
import schemas

router = APIRouter()


@router.get("/", response_model=List[schemas.TaxFilingResponse])
def list_tax_filings(
    client_id: Optional[int] = None,
    month: Optional[int] = None,
    year: Optional[int] = None,
    filing_type: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(models.TaxFiling)
    if client_id:
        q = q.filter(models.TaxFiling.client_id == client_id)
    if month:
        q = q.filter(models.TaxFiling.month == month)
    if year:
        q = q.filter(models.TaxFiling.year == year)
    if filing_type:
        q = q.filter(models.TaxFiling.filing_type == filing_type)
    if status:
        q = q.filter(models.TaxFiling.status == status)
    return q.order_by(models.TaxFiling.due_date).all()


@router.post("/", response_model=schemas.TaxFilingResponse, status_code=201)
def create_tax_filing(data: schemas.TaxFilingCreate, db: Session = Depends(get_db)):
    filing = models.TaxFiling(**data.model_dump())
    db.add(filing)
    db.commit()
    db.refresh(filing)
    return filing


@router.get("/{filing_id}", response_model=schemas.TaxFilingResponse)
def get_tax_filing(filing_id: int, db: Session = Depends(get_db)):
    filing = db.query(models.TaxFiling).filter(models.TaxFiling.id == filing_id).first()
    if not filing:
        raise HTTPException(status_code=404, detail="ไม่พบรายการ")
    return filing


@router.put("/{filing_id}", response_model=schemas.TaxFilingResponse)
def update_tax_filing(filing_id: int, data: schemas.TaxFilingUpdate, db: Session = Depends(get_db)):
    filing = db.query(models.TaxFiling).filter(models.TaxFiling.id == filing_id).first()
    if not filing:
        raise HTTPException(status_code=404, detail="ไม่พบรายการ")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(filing, k, v)
    db.commit()
    db.refresh(filing)
    return filing


@router.delete("/{filing_id}", status_code=204)
def delete_tax_filing(filing_id: int, db: Session = Depends(get_db)):
    filing = db.query(models.TaxFiling).filter(models.TaxFiling.id == filing_id).first()
    if not filing:
        raise HTTPException(status_code=404, detail="ไม่พบรายการ")
    db.delete(filing)
    db.commit()
