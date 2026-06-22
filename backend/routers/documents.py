from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
import models
import schemas
import bill_parser

router = APIRouter()


@router.post("/parse-pdf")
async def parse_pdf(file: UploadFile = File(...)):
    """อ่านบิลจาก PDF ด้วย Claude vision → คืน JSON preview (ยังไม่บันทึกลง DB)"""
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="กรุณาอัปโหลดไฟล์ PDF")
    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="ไฟล์ว่างเปล่า")
    try:
        data = bill_parser.parse_bill_pdf(pdf_bytes)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"อ่านบิลไม่สำเร็จ: {e}")
    return {"filename": file.filename, "parsed": data}


@router.get("/", response_model=List[schemas.DocumentResponse])
def list_documents(
    client_id: Optional[int] = None,
    month: Optional[int] = None,
    year: Optional[int] = None,
    db: Session = Depends(get_db),
):
    q = db.query(models.Document)
    if client_id:
        q = q.filter(models.Document.client_id == client_id)
    if month:
        q = q.filter(models.Document.month == month)
    if year:
        q = q.filter(models.Document.year == year)
    return q.order_by(models.Document.received_date.desc()).all()


@router.post("/", response_model=schemas.DocumentResponse, status_code=201)
def create_document(data: schemas.DocumentCreate, db: Session = Depends(get_db)):
    doc = models.Document(**data.model_dump())
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@router.put("/{doc_id}", response_model=schemas.DocumentResponse)
def update_document(doc_id: int, data: schemas.DocumentUpdate, db: Session = Depends(get_db)):
    doc = db.query(models.Document).filter(models.Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="ไม่พบเอกสาร")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(doc, k, v)
    db.commit()
    db.refresh(doc)
    return doc


@router.delete("/{doc_id}", status_code=204)
def delete_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(models.Document).filter(models.Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="ไม่พบเอกสาร")
    db.delete(doc)
    db.commit()
