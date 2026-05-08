from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from app.database import Base
from datetime import datetime

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    destination_country = Column(String, nullable=True)
    course_of_interest = Column(String, nullable=True)
    budget = Column(String, nullable=True)
    qualifications = Column(String, nullable=True)
    ielts_score = Column(String, nullable=True)
    pipeline_stage = Column(String, default="new")  # new → qualified → docs_received → applied → enrolled
    needs_human = Column(Boolean, default=False)
    last_message_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    student_phone = Column(String, nullable=False)
    doc_type = Column(String, nullable=False)  # passport, transcript, ielts, statement_of_finance
    status = Column(String, default="pending")  # pending, received
    submitted_at = Column(DateTime, nullable=True)

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String, nullable=False)
    role = Column(String, nullable=False)  # user or assistant
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
