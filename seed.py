"""
CliniQ Database Seed Script
Run with: python seed.py
Populates the database with realistic doctors, patients, and time slots
"""

from app.database import SessionLocal, engine, Base
from app.models import Patient, Doctor, TimeSlot
from datetime import date, time, timedelta

Base.metadata.create_all(bind=engine)
db = SessionLocal()

print("🌱 Seeding CliniQ database...")

# ── Clear existing data ──────────────────────────────────────────
# ── Clear existing data (order matters — respect foreign keys) ───
from app.models import Appointment
db.query(Appointment).delete()
db.query(TimeSlot).delete()
db.query(Patient).delete()
db.query(Doctor).delete()
db.commit()

# ── Doctors ──────────────────────────────────────────────────────
doctors_data = [
    {"full_name": "Dr. Sarah Johnson",   "specialty": "General Practice",  "phone": "+2348011111111", "email": "sarah.johnson@cliniq.com"},
    {"full_name": "Dr. Michael Okafor",  "specialty": "Cardiology",        "phone": "+2348022222222", "email": "michael.okafor@cliniq.com"},
    {"full_name": "Dr. Amina Hassan",    "specialty": "Gynecology",        "phone": "+2348033333333", "email": "amina.hassan@cliniq.com"},
    {"full_name": "Dr. James Adeyemi",   "specialty": "Pediatrics",        "phone": "+2348044444444", "email": "james.adeyemi@cliniq.com"},
    {"full_name": "Dr. Linda Chukwu",    "specialty": "Dermatology",       "phone": "+2348055555555", "email": "linda.chukwu@cliniq.com"},
    {"full_name": "Dr. Emmanuel Nwachukwu", "specialty": "Orthopedics",    "phone": "+2348066666666", "email": "emmanuel.nwachukwu@cliniq.com"},
    {"full_name": "Dr. Fatima Aliyu",    "specialty": "Ophthalmology",     "phone": "+2348077777777", "email": "fatima.aliyu@cliniq.com"},
    {"full_name": "Dr. Charles Eze",     "specialty": "Dentistry",         "phone": "+2348088888888", "email": "charles.eze@cliniq.com"},
]

doctors = []
for d in doctors_data:
    doctor = Doctor(**d, is_available=True)
    db.add(doctor)
    doctors.append(doctor)

db.commit()
for d in doctors:
    db.refresh(d)
print(f"✅ Added {len(doctors)} doctors")

# ── Patients ─────────────────────────────────────────────────────
patients_data = [
    {"reg_number": "CLQ001", "full_name": "John Doe",          "phone": "+2349075057294", "email": "john.doe@email.com"},
    {"reg_number": "CLQ002", "full_name": "Aisha Mohammed",    "phone": "+2348100000001", "email": "aisha.m@email.com"},
    {"reg_number": "CLQ003", "full_name": "Emeka Obi",         "phone": "+2348100000002", "email": "emeka.obi@email.com"},
    {"reg_number": "CLQ004", "full_name": "Ngozi Adaeze",      "phone": "+2348100000003", "email": "ngozi.a@email.com"},
    {"reg_number": "CLQ005", "full_name": "Tunde Bakare",      "phone": "+2348100000004", "email": "tunde.b@email.com"},
    {"reg_number": "CLQ006", "full_name": "Chioma Eze",        "phone": "+2348100000005", "email": "chioma.e@email.com"},
    {"reg_number": "CLQ007", "full_name": "Ibrahim Musa",      "phone": "+2348100000006", "email": "ibrahim.m@email.com"},
    {"reg_number": "CLQ008", "full_name": "Grace Okonkwo",     "phone": "+2348100000007", "email": "grace.o@email.com"},
    {"reg_number": "CLQ009", "full_name": "David Adeleke",     "phone": "+2348100000008", "email": "david.a@email.com"},
    {"reg_number": "CLQ010", "full_name": "Blessing Nwosu",    "phone": "+2348100000009", "email": "blessing.n@email.com"},
]

for p in patients_data:
    patient = Patient(**p)
    db.add(patient)

db.commit()
print(f"✅ Added {len(patients_data)} patients")

# ── Time Slots ────────────────────────────────────────────────────
# Generate slots for the next 14 days
# Morning: 9am - 12pm, Afternoon: 2pm - 5pm
# Skip Sundays

morning_slots = [
    (time(9, 0),  time(9, 30)),
    (time(9, 30), time(10, 0)),
    (time(10, 0), time(10, 30)),
    (time(10, 30),time(11, 0)),
    (time(11, 0), time(11, 30)),
    (time(11, 30),time(12, 0)),
]

afternoon_slots = [
    (time(14, 0), time(14, 30)),
    (time(14, 30),time(15, 0)),
    (time(15, 0), time(15, 30)),
    (time(15, 30),time(16, 0)),
    (time(16, 0), time(16, 30)),
    (time(16, 30),time(17, 0)),
]

all_slots = morning_slots + afternoon_slots
slot_count = 0
today = date.today()

for day_offset in range(1, 15):  # Next 14 days
    slot_date = today + timedelta(days=day_offset)

    # Skip Sundays (weekday 6)
    if slot_date.weekday() == 6:
        continue

    for doctor in doctors:
        # Not all doctors work every day — simulate realistic availability
        # Doctors work 5 days a week, skip one weekday randomly based on doctor id
        if slot_date.weekday() == (doctor.id % 5):
            continue

        for start_time, end_time in all_slots:
            slot = TimeSlot(
                doctor_id=doctor.id,
                date=slot_date,
                start_time=start_time,
                end_time=end_time,
                is_booked=False
            )
            db.add(slot)
            slot_count += 1

db.commit()
print(f"✅ Added {slot_count} time slots across 14 days")

# ── Summary ───────────────────────────────────────────────────────
print("\n📊 Database Summary:")
print(f"   Doctors:  {db.query(Doctor).count()}")
print(f"   Patients: {db.query(Patient).count()}")
print(f"   Slots:    {db.query(TimeSlot).count()}")
print("\n🏥 Doctors added:")
for d in db.query(Doctor).all():
    slot_count = db.query(TimeSlot).filter(TimeSlot.doctor_id == d.id).count()
    print(f"   - {d.full_name} ({d.specialty}) → {slot_count} slots")

print("\n👥 Patient reg numbers:")
for p in db.query(Patient).all():
    print(f"   - {p.reg_number} → {p.full_name}")

print("\n✅ Seeding complete! CliniQ is ready.")
db.close()