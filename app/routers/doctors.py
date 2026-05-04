from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Doctor, TimeSlot
from app.schemas import DoctorCreate, DoctorOut, SlotOut
from datetime import date

router = APIRouter(prefix="/doctors", tags=["Doctors"])


@router.post("/", response_model=DoctorOut)
def create_doctor(doctor: DoctorCreate, db: Session = Depends(get_db)):
    new_doctor = Doctor(
        full_name=doctor.full_name,
        specialty=doctor.specialty,
        phone=doctor.phone,
        email=doctor.email
    )
    db.add(new_doctor)
    db.commit()
    db.refresh(new_doctor)
    return new_doctor


@router.get("/", response_model=list[DoctorOut])
def list_doctors(db: Session = Depends(get_db)):
    return db.query(Doctor).filter(Doctor.is_available == True).all()


@router.get("/{doctor_id}/slots", response_model=list[SlotOut])
def get_doctor_slots(doctor_id: int, date: date = None, db: Session = Depends(get_db)):
    query = db.query(TimeSlot).filter(
        TimeSlot.doctor_id == doctor_id,
        TimeSlot.is_booked == False
    )
    if date:
        query = query.filter(TimeSlot.date == date)
    return query.all()


@router.post("/{doctor_id}/slots")
def add_slot(doctor_id: int, slot: SlotOut, db: Session = Depends(get_db)):
    new_slot = TimeSlot(
        doctor_id=doctor_id,
        date=slot.date,
        start_time=slot.start_time,
        end_time=slot.end_time
    )
    db.add(new_slot)
    db.commit()
    db.refresh(new_slot)
    return new_slot
