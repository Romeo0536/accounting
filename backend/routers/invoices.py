from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from database import get_db
import models
import schemas

router = APIRouter()


def generate_invoice_number(db: Session) -> str:
    year = date.today().year
    count = db.query(models.Invoice).filter(
        models.Invoice.invoice_number.like(f"INV-{year}-%")
    ).count()
    return f"INV-{year}-{count + 1:04d}"


@router.get("/", response_model=List[schemas.InvoiceResponse])
def list_invoices(
    client_id: Optional[int] = None,
    status: Optional[str] = None,
    year: Optional[int] = None,
    db: Session = Depends(get_db),
):
    q = db.query(models.Invoice)
    if client_id:
        q = q.filter(models.Invoice.client_id == client_id)
    if status:
        q = q.filter(models.Invoice.status == status)
    if year:
        q = q.filter(models.Invoice.service_year == year)
    return q.order_by(models.Invoice.invoice_date.desc()).all()


@router.post("/", response_model=schemas.InvoiceResponse, status_code=201)
def create_invoice(data: schemas.InvoiceCreate, db: Session = Depends(get_db)):
    items_data = data.items
    inv_data = data.model_dump(exclude={"items"})
    inv_data["invoice_number"] = generate_invoice_number(db)
    invoice = models.Invoice(**inv_data)
    db.add(invoice)
    db.flush()
    for item in items_data:
        db.add(models.InvoiceItem(invoice_id=invoice.id, **item.model_dump()))
    db.commit()
    db.refresh(invoice)
    return invoice


@router.get("/{invoice_id}", response_model=schemas.InvoiceResponse)
def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    inv = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="ไม่พบใบแจ้งหนี้")
    return inv


@router.put("/{invoice_id}", response_model=schemas.InvoiceResponse)
def update_invoice(invoice_id: int, data: schemas.InvoiceUpdate, db: Session = Depends(get_db)):
    inv = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="ไม่พบใบแจ้งหนี้")
    update_data = data.model_dump(exclude_none=True)
    items_data = update_data.pop("items", None)
    for k, v in update_data.items():
        setattr(inv, k, v)
    if items_data is not None:
        for item in inv.items:
            db.delete(item)
        for item in items_data:
            db.add(models.InvoiceItem(invoice_id=inv.id, **item))
    db.commit()
    db.refresh(inv)
    return inv


@router.post("/{invoice_id}/mark-paid", response_model=schemas.InvoiceResponse)
def mark_paid(invoice_id: int, paid_date: Optional[date] = None, db: Session = Depends(get_db)):
    inv = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="ไม่พบใบแจ้งหนี้")
    inv.status = "paid"
    inv.paid_date = paid_date or date.today()
    db.commit()
    db.refresh(inv)
    return inv


@router.delete("/{invoice_id}", status_code=204)
def delete_invoice(invoice_id: int, db: Session = Depends(get_db)):
    inv = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="ไม่พบใบแจ้งหนี้")
    db.delete(inv)
    db.commit()
