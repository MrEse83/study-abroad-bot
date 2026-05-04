from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Appointment, Patient, Doctor, TimeSlot
from app.schemas import AppointmentCreate, AppointmentOut
from app.services.notifications import trigger_n8n_notification

router = APIRouter(prefix="/appointments", tags=["Appointments"])


@router.get("/", response_model=list[AppointmentOut])
def list_appointments(db: Session = Depends(get_db)):
    return db.query(Appointment).all()


@router.get("/{appointment_id}", response_model=AppointmentOut)
def get_appointment(appointment_id: int, db: Session = Depends(get_db)):
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found.")
    return appt
