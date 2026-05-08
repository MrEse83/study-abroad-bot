from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from app.database import SessionLocal
from app.models import Student, Document
import os

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

UPLOAD_DIR = "uploads"


@router.get("/")
def serve_dashboard():
    """Serve the dashboard HTML file."""
    return FileResponse("static/index.html")


@router.get("/students")
def get_all_students():
    """Return all students with their pipeline stage and doc counts."""
    db = SessionLocal()
    try:
        students = db.query(Student).order_by(Student.last_message_at.desc()).all()
        result = []
        for s in students:
            docs = db.query(Document).filter(
                Document.student_phone == s.phone,
                Document.status == "received"
            ).all()
            result.append({
                "id": s.id,
                "phone": s.phone,
                "full_name": s.full_name or "Unknown",
                "destination_country": s.destination_country or "—",
                "course_of_interest": s.course_of_interest or "—",
                "budget": s.budget or "—",
                "qualifications": s.qualifications or "—",
                "ielts_score": s.ielts_score or "Not taken",
                "pipeline_stage": s.pipeline_stage or "new",
                "needs_human": s.needs_human,
                "last_message_at": s.last_message_at.isoformat() if s.last_message_at else None,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "docs_received": len(docs),
                "docs_total": 4,
                "documents": [{"doc_type": d.doc_type, "submitted_at": d.submitted_at.isoformat() if d.submitted_at else None} for d in docs]
            })
        return result
    finally:
        db.close()


@router.get("/student/{phone}")
def get_student(phone: str):
    """Return a single student's full profile and documents."""
    db = SessionLocal()
    try:
        # Try matching with and without country code prefix
        student = (
            db.query(Student).filter(Student.phone == f"whatsapp:+{phone}").first()
            or db.query(Student).filter(Student.phone == phone).first()
        )
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")

        docs = db.query(Document).filter(
            Document.student_phone == student.phone,
            Document.status == "received"
        ).all()

        return {
            "id": student.id,
            "phone": student.phone,
            "full_name": student.full_name or "Unknown",
            "destination_country": student.destination_country or "—",
            "course_of_interest": student.course_of_interest or "—",
            "budget": student.budget or "—",
            "qualifications": student.qualifications or "—",
            "ielts_score": student.ielts_score or "Not taken",
            "pipeline_stage": student.pipeline_stage or "new",
            "needs_human": student.needs_human,
            "last_message_at": student.last_message_at.isoformat() if student.last_message_at else None,
            "created_at": student.created_at.isoformat() if student.created_at else None,
            "documents": [
                {
                    "doc_type": d.doc_type,
                    "status": d.status,
                    "submitted_at": d.submitted_at.isoformat() if d.submitted_at else None,
                    "download_url": f"/dashboard/document/{student.phone.replace('whatsapp:+', '')}/{d.doc_type}"
                }
                for d in docs
            ]
        }
    finally:
        db.close()


@router.get("/document/{phone}/{doc_type}")
def download_document(phone: str, doc_type: str):
    """Download a specific document for a student."""
    # Find matching file in uploads directory
    matches = [
        f for f in os.listdir(UPLOAD_DIR)
        if phone in f and doc_type in f
    ]
    if not matches:
        raise HTTPException(status_code=404, detail="Document not found")

    # Return most recent match
    matches.sort(reverse=True)
    file_path = os.path.join(UPLOAD_DIR, matches[0])
    return FileResponse(file_path, filename=matches[0])


@router.get("/stats")
def get_stats():
    """Return pipeline summary stats for the dashboard overview."""
    db = SessionLocal()
    try:
        total = db.query(Student).count()
        new = db.query(Student).filter(Student.pipeline_stage == "new").count()
        qualified = db.query(Student).filter(Student.pipeline_stage == "qualified").count()
        docs_received = db.query(Student).filter(Student.pipeline_stage == "docs_received").count()
        applied = db.query(Student).filter(Student.pipeline_stage == "applied").count()
        enrolled = db.query(Student).filter(Student.pipeline_stage == "enrolled").count()
        needs_human = db.query(Student).filter(Student.needs_human == True).count()

        return {
            "total": total,
            "new": new,
            "qualified": qualified,
            "docs_received": docs_received,
            "applied": applied,
            "enrolled": enrolled,
            "needs_human": needs_human
        }
    finally:
        db.close()
