from sqlalchemy.orm import Session
from app.models import TimeSlot, Doctor
from datetime import date


def get_available_slots(db: Session, doctor_id: int, date: date):
    return db.query(TimeSlot).filter(
        TimeSlot.doctor_id == doctor_id,
        TimeSlot.date == date,
        TimeSlot.is_booked == False
    ).all()


def get_next_available_slots(db: Session, doctor_id: int, limit: int = 3):
    from datetime import date as today_date
    return db.query(TimeSlot).filter(
        TimeSlot.doctor_id == doctor_id,
        TimeSlot.date >= today_date.today(),
        TimeSlot.is_booked == False
    ).order_by(TimeSlot.date, TimeSlot.start_time).limit(limit).all()


def get_all_doctors(db: Session):
    return db.query(Doctor).filter(Doctor.is_available == True).all()


def get_doctor_by_specialty(db: Session, specialty: str):
    return db.query(Doctor).filter(
        Doctor.specialty.ilike(f"%{specialty}%"),
        Doctor.is_available == True
    ).all()
