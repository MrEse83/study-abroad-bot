import os
import httpx
from datetime import datetime
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Student, Document

# Supported file types
SUPPORTED_DOCS = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "image/jpeg": "jpg",
    "image/png": "png"
}

# Max number of documents we accept per student
MAX_DOCS = 4

# Where to save downloaded files
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def download_twilio_media(media_url: str, filename: str) -> str:
    """Download a file from Twilio media URL with Basic Auth."""
    from app.config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN

    save_path = os.path.join(UPLOAD_DIR, filename)
    try:
        with httpx.Client() as client:
            response = client.get(
                media_url,
                auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
                follow_redirects=True,
                timeout=30
            )
            response.raise_for_status()
            with open(save_path, "wb") as f:
                f.write(response.content)
        print(f"✅ File downloaded: {save_path}")
        return save_path
    except Exception as e:
        print(f"❌ Failed to download media: {e}")
        return None


def handle_document(phone: str, media_url: str, media_type: str) -> str:
    """
    Handle incoming document from a student.
    - No content verification — consultant reviews manually
    - Student can send multiple docs one after the other
    - Notifies consultant when MAX_DOCS are received
    - Uses DB-level count to avoid race conditions
    """
    db: Session = SessionLocal()

    try:
        # 1. Validate file type
        if media_type not in SUPPORTED_DOCS:
            return (
                "Sorry, I can only accept PDF, Word documents, or images (JPG/PNG). "
                "Please send your documents in one of those formats. 📎"
            )

        # 2. Check student exists
        student = db.query(Student).filter(Student.phone == phone).first()
        if not student:
            return (
                "I don't have your profile yet. Please tell me your name first "
                "so I can get you set up. 😊"
            )

        # 3. Count existing docs using DB aggregate (avoids race condition)
        doc_count = db.query(func.count(Document.id)).filter(
            Document.student_phone == phone,
            Document.status == "received"
        ).scalar() or 0

        if doc_count >= MAX_DOCS:
            return (
                "✅ We already have all your documents. "
                "A consultant will reach out to you shortly! 😊"
            )

        # 4. Download file from Twilio
        file_ext = SUPPORTED_DOCS[media_type]
        safe_phone = phone.replace("whatsapp:+", "").replace("+", "")
        # Use timestamp in filename to avoid duplicates when multiple docs sent at once
        timestamp = int(datetime.utcnow().timestamp() * 1000)  # milliseconds
        filename = f"{safe_phone}_{timestamp}.{file_ext}"
        local_path = download_twilio_media(media_url, filename)

        if not local_path:
            return (
                "⚠️ I had trouble saving your document. "
                "Please try sending it again."
            )

        # 5. Save Document record — use timestamp as doc_type to avoid duplicate keys
        doc = Document(
            student_phone=phone,
            doc_type=f"document_{timestamp}",
            status="received",
            submitted_at=datetime.utcnow()
        )
        db.add(doc)
        db.flush()  # flush to DB before counting again

        # 6. Re-count after insert to get accurate total
        new_count = db.query(func.count(Document.id)).filter(
            Document.student_phone == phone,
            Document.status == "received"
        ).scalar() or 0

        student.last_message_at = datetime.utcnow()

        # 7. All docs received — notify consultant
        if new_count >= MAX_DOCS:
            student.pipeline_stage = "docs_received"
            student.needs_human = True
            db.commit()

            print(f"🎉 ALL {MAX_DOCS} DOCS RECEIVED for {phone}")

            student_data = {
                "full_name": student.full_name,
                "destination_country": student.destination_country,
                "course_of_interest": student.course_of_interest,
                "budget": student.budget,
                "qualifications": student.qualifications,
                "ielts_score": student.ielts_score,
                "pipeline_stage": "docs_received"
            }

            from app.services.escalate import notify_consultant
            notify_consultant(
                phone=phone,
                reason=f"All {MAX_DOCS} documents received. Ready for consultant review.",
                student_data=student_data
            )

            return (
                "✅ All documents received! Thank you.\n\n"
                "Our consultant will review everything and reach out to you directly. "
                "We'll be in touch soon! 🌍📚"
            )

        db.commit()

        # 8. Acknowledge and show progress
        remaining = MAX_DOCS - new_count
        return (
            f"✅ Document {new_count} of {MAX_DOCS} received.\n\n"
            f"Please send the remaining {remaining} document{'s' if remaining > 1 else ''}. "
            f"You can send them one after the other. 😊"
        )

    except Exception as e:
        print(f"❌ Error in handle_document: {e}")
        db.rollback()
        return "Sorry, something went wrong. Please try again in a moment."

    finally:
        db.close()