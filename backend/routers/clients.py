from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
import models
import schemas
import automation

router = APIRouter()


def generate_client_code(db: Session) -> str:
    last = db.query(models.Client).order_by(models.Client.id.desc()).first()
    if not last:
        return "AC001"
    num = int(last.code[2:]) + 1 if last.code and last.code.startswith("AC") else 1
    return f"AC{num:03d}"


@router.get("/", response_model=List[schemas.ClientResponse])
def list_clients(status: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(models.Client)
    if status:
        q = q.filter(models.Client.status == status)
    return q.order_by(models.Client.code).all()


@router.post("/", response_model=schemas.ClientResponse, status_code=201)
def create_client(data: schemas.ClientCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    client = models.Client(**data.model_dump(), code=generate_client_code(db))
    db.add(client)
    db.commit()
    db.refresh(client)
    # Auto onboarding: สร้างงานเดือนปัจจุบัน + รายการภาษีในพื้นหลัง
    background_tasks.add_task(automation.auto_onboard_client, client.id)
    return client


@router.get("/{client_id}", response_model=schemas.ClientResponse)
def get_client(client_id: int, db: Session = Depends(get_db)):
    client = db.query(models.Client).filter(models.Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="ไม่พบลูกค้า")
    return client


@router.put("/{client_id}", response_model=schemas.ClientResponse)
def update_client(client_id: int, data: schemas.ClientUpdate, db: Session = Depends(get_db)):
    client = db.query(models.Client).filter(models.Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="ไม่พบลูกค้า")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(client, k, v)
    db.commit()
    db.refresh(client)
    return client


@router.delete("/{client_id}", status_code=204)
def delete_client(client_id: int, db: Session = Depends(get_db)):
    client = db.query(models.Client).filter(models.Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="ไม่พบลูกค้า")
    db.delete(client)
    db.commit()
