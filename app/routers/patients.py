from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Patient
from app.schemas import PatientCreate, PatientOut

router = APIRouter(prefix="/patients", tags=["Patients"])


@router.post("/register", response_model=PatientOut)
def register_patient(patient: PatientCreate, db: Session = Depends(get_db)):
    existing = db.query(Patient).filter(
        Patient.reg_number == patient.reg_number.upper()
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Registration number already exists.")

    new_patient = Patient(
        reg_number=patient.reg_number.upper(),
        full_name=patient.full_name,
        phone=patient.phone,
        email=patient.email
    )
    db.add(new_patient)
    db.commit()
    db.refresh(new_patient)
    return new_patient


@router.get("/{reg_number}", response_model=PatientOut)
def get_patient(reg_number: str, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(
        Patient.reg_number == reg_number.upper()
    ).first()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found.")
    return patient
