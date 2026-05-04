from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from sqlalchemy.orm import Session
from app.models import Patient, Doctor, TimeSlot, Appointment
from app.config import OPENAI_API_KEY
from datetime import datetime
from typing import Optional
import json

# One MemorySaver per phone number — keeps conversation history
conversation_memories = {}


def get_checkpointer(phone: str) -> MemorySaver:
    if phone not in conversation_memories:
        conversation_memories[phone] = MemorySaver()
    return conversation_memories[phone]


def clear_memory(phone: str):
    if phone in conversation_memories:
        del conversation_memories[phone]


SYSTEM_PROMPT = """You are CliniQ, a friendly and professional AI assistant for a medical clinic.
Your job is to help patients book appointments with doctors via WhatsApp.

Follow this flow:
1. Greet the patient warmly
2. Ask for their registration number to verify they are registered
3. Ask what type of doctor or specialty they need (or list available doctors)
4. Ask for their preferred date
5. Show available time slots and let them choose
6. Confirm the booking

Rules:
- Always verify the patient registration number first using check_patient tool
- If patient is not registered, tell them to visit the clinic to register. Registration desk: 08012345678
- Be conversational and friendly, not robotic
- If no slots are available on their preferred date, suggest the next available slots
- Always confirm appointment details before finalising
- Keep responses short and clear — this is WhatsApp, not email
- After a successful booking, tell them they will receive a confirmation message shortly
"""


def build_tools(db: Session):

    @tool
    def check_patient(reg_number: str) -> str:
        """Check if a patient exists using their registration number."""
        patient = db.query(Patient).filter(
            Patient.reg_number == reg_number.strip().upper()
        ).first()

        if patient:
            return json.dumps({
                "found": True,
                "patient_id": patient.id,
                "name": patient.full_name,
                "reg_number": patient.reg_number
            })
        return json.dumps({
            "found": False,
            "message": "Patient not registered."
        })

    @tool
    def list_doctors(specialty: str = "") -> str:
        """List all available doctors. Pass specialty to filter, or empty string for all."""
        query = db.query(Doctor).filter(Doctor.is_available == True)
        if specialty:
            query = query.filter(Doctor.specialty.ilike(f"%{specialty}%"))
        doctors = query.all()

        if not doctors:
            return "No doctors found."

        result = [{"id": d.id, "name": d.full_name, "specialty": d.specialty} for d in doctors]
        return json.dumps(result)

    @tool
    def check_availability(doctor_id: int, date: str) -> str:
        """Check available time slots for a doctor on a specific date. Date format: YYYY-MM-DD"""
        try:
            parsed_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            return "Invalid date format. Please use YYYY-MM-DD."

        slots = db.query(TimeSlot).filter(
            TimeSlot.doctor_id == doctor_id,
            TimeSlot.date == parsed_date,
            TimeSlot.is_booked == False
        ).all()

        if not slots:
            next_slots = db.query(TimeSlot).filter(
                TimeSlot.doctor_id == doctor_id,
                TimeSlot.date >= datetime.today().date(),
                TimeSlot.is_booked == False
            ).order_by(TimeSlot.date, TimeSlot.start_time).limit(3).all()

            if next_slots:
                suggestions = [
                    {"slot_id": s.id, "date": str(s.date),
                     "start_time": str(s.start_time), "end_time": str(s.end_time)}
                    for s in next_slots
                ]
                return json.dumps({
                    "available": False,
                    "message": "No slots on that date. Next available:",
                    "suggestions": suggestions
                })
            return json.dumps({"available": False, "message": "No available slots for this doctor."})

        available = [
            {"slot_id": s.id, "date": str(s.date),
             "start_time": str(s.start_time), "end_time": str(s.end_time)}
            for s in slots
        ]
        return json.dumps({"available": True, "slots": available})

    @tool
    def book_appointment(reg_number: str, doctor_id: int, slot_id: int, reason: str = "") -> str:
        """Book an appointment. Requires reg_number, doctor_id, and slot_id."""
        patient = db.query(Patient).filter(
            Patient.reg_number == reg_number.strip().upper()
        ).first()

        if not patient:
            return "Patient not found. Cannot book appointment."

        slot = db.query(TimeSlot).filter(
            TimeSlot.id == slot_id,
            TimeSlot.is_booked == False
        ).first()

        if not slot:
            return "That slot is no longer available. Please choose another."

        doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
        if not doctor:
            return "Doctor not found."

        appointment = Appointment(
            patient_id=patient.id,
            doctor_id=doctor_id,
            slot_id=slot_id,
            reason=reason or None,
            status="confirmed"
        )
        db.add(appointment)
        slot.is_booked = True
        db.commit()
        db.refresh(appointment)

        return json.dumps({
            "success": True,
            "appointment_id": appointment.id,
            "patient_name": patient.full_name,
            "doctor_name": doctor.full_name,
            "specialty": doctor.specialty,
            "date": str(slot.date),
            "time": str(slot.start_time),
            "status": "confirmed"
        })

    return [check_patient, list_doctors, check_availability, book_appointment]


def get_agent_response(message: str, phone: str, db: Session) -> str:
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0.3,
        api_key=OPENAI_API_KEY
    )

    tools = build_tools(db)
    checkpointer = get_checkpointer(phone)

    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer
    )

    config = {"configurable": {"thread_id": phone}}

    response = agent.invoke(
        {"messages": [HumanMessage(content=message)]},
        config=config
    )

    return response["messages"][-1].content