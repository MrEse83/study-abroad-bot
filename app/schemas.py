from pydantic import BaseModel
from typing import Optional
from datetime import date, time, datetime


class PatientCreate(BaseModel):
    reg_number: str
    full_name: str
    phone: str
    email: Optional[str] = None


class PatientOut(BaseModel):
    id: int
    reg_number: str
    full_name: str
    phone: str
    email: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class DoctorCreate(BaseModel):
    full_name: str
    specialty: str
    phone: str
    email: Optional[str] = None


class DoctorOut(BaseModel):
    id: int
    full_name: str
    specialty: str
    is_available: bool

    class Config:
        from_attributes = True


class SlotOut(BaseModel):
    id: int
    date: date
    start_time: time
    end_time: time
    is_booked: bool

    class Config:
        from_attributes = True


class AppointmentCreate(BaseModel):
    reg_number: str
    doctor_id: int
    slot_id: int
    reason: Optional[str] = None


class AppointmentOut(BaseModel):
    id: int
    status: str
    created_at: datetime
    patient: PatientOut
    doctor: DoctorOut

    class Config:
        from_attributes = True


class WhatsAppMessage(BaseModel):
    From: str
    Body: str
