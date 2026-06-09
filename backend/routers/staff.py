from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
import models
import schemas

router = APIRouter()


@router.get("/", response_model=List[schemas.StaffResponse])
def list_staff(db: Session = Depends(get_db)):
    return db.query(models.Staff).order_by(models.Staff.name).all()


@router.post("/", response_model=schemas.StaffResponse, status_code=201)
def create_staff(data: schemas.StaffCreate, db: Session = Depends(get_db)):
    staff = models.Staff(**data.model_dump())
    db.add(staff)
    db.commit()
    db.refresh(staff)
    return staff


@router.get("/{staff_id}", response_model=schemas.StaffResponse)
def get_staff(staff_id: int, db: Session = Depends(get_db)):
    staff = db.query(models.Staff).filter(models.Staff.id == staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="ไม่พบพนักงาน")
    return staff


@router.put("/{staff_id}", response_model=schemas.StaffResponse)
def update_staff(staff_id: int, data: schemas.StaffUpdate, db: Session = Depends(get_db)):
    staff = db.query(models.Staff).filter(models.Staff.id == staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="ไม่พบพนักงาน")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(staff, k, v)
    db.commit()
    db.refresh(staff)
    return staff


@router.delete("/{staff_id}", status_code=204)
def delete_staff(staff_id: int, db: Session = Depends(get_db)):
    staff = db.query(models.Staff).filter(models.Staff.id == staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="ไม่พบพนักงาน")
    db.delete(staff)
    db.commit()
