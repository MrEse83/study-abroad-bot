import os
import httpx
from datetime import datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Student, Document

# Map content types to file extensions
SUPPORTED_DOCS = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "image/jpeg": "jpg",
    "image/png": "png"
}

# Expected documents per student (in order)
REQUIRED_DOCS = ["passport", "transcript", "ielts_result", "statement_of_finance"]

# Friendly names for display
DOC_LABELS = {
    "passport": "Passport / ID",
    "transcript": "Academic Transcript",
    "ielts_result": "IELTS Result",
    "statement_of_finance": "Statement of Finance"
}

# Where to save downloaded files locally
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def download_twilio_media(media_url: str, filename: str) -> str:
    """
    Download a file from Twilio's media URL (requires Basic Auth).
    Saves it locally and returns the saved file path.
    """
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
    Handle an incoming document from a student on WhatsApp.
    - Validates file type
    - Checks student exists
    - Downloads the file from Twilio
    - Saves a Document record in the DB
    - Notifies consultant when all docs are received
    """
    db: Session = SessionLocal()

    try:
        # --- 1. Validate file type ---
        if media_type not in SUPPORTED_DOCS:
            return (
                "Sorry, I can only accept PDF, Word documents, or images (JPG/PNG). "
                "Please send your document in one of those formats. 📎"
            )

        # --- 2. Check student exists ---
        student = db.query(Student).filter(Student.phone == phone).first()
        if not student:
            return (
                "I don't have your profile yet. Please tell me your name first "
                "so I can get you set up. 😊"
            )

        # --- 3. Figure out which doc is next ---
        submitted_docs = db.query(Document).filter(
            Document.student_phone == phone,
            Document.status == "received"
        ).all()

        submitted_types = [d.doc_type for d in submitted_docs]
        pending_docs = [d for d in REQUIRED_DOCS if d not in submitted_types]

        if not pending_docs:
            return (
                "✅ We already have all your documents on file. "
                "A consultant will be in touch with you shortly!"
            )

        next_doc_type = pending_docs[0]
        file_ext = SUPPORTED_DOCS[media_type]

        # --- 4. Download file from Twilio ---
        safe_phone = phone.replace("whatsapp:+", "").replace("+", "")
        filename = f"{safe_phone}_{next_doc_type}_{int(datetime.utcnow().timestamp())}.{file_ext}"
        local_path = download_twilio_media(media_url, filename)

        if not local_path:
            return (
                "⚠️ I had trouble saving your document. "
                "Please try sending it again."
            )

        # --- 5. Save Document record in DB ---
        doc = Document(
            student_phone=phone,
            doc_type=next_doc_type,
            status="received",
            submitted_at=datetime.utcnow()
        )
        db.add(doc)

        # --- 6. Check if all docs are now received ---
        newly_submitted = submitted_types + [next_doc_type]
        all_received = all(d in newly_submitted for d in REQUIRED_DOCS)

        if all_received:
            student.pipeline_stage = "docs_received"
            student.needs_human = True
            print(f"🎉 ALL DOCS RECEIVED for {phone} — notifying consultant")

            # Build student data dict for notification
            student_data = {
                "full_name": student.full_name,
                "destination_country": student.destination_country,
                "course_of_interest": student.course_of_interest,
                "budget": student.budget,
                "qualifications": student.qualifications,
                "ielts_score": student.ielts_score,
                "pipeline_stage": "docs_received"
            }

            # 🚀 Notify consultant
            from app.services.escalate import notify_consultant
            notify_consultant(
                phone=phone,
                reason="All required documents have been submitted. Student is ready for consultation.",
                student_data=student_data
            )

        student.last_message_at = datetime.utcnow()
        db.commit()

        # --- 7. Build reply to student ---
        doc_label = DOC_LABELS.get(next_doc_type, next_doc_type.replace("_", " ").title())
        remaining = [DOC_LABELS.get(d, d) for d in REQUIRED_DOCS if d not in newly_submitted]

        if remaining:
            remaining_list = "\n".join([f"• {d}" for d in remaining])
            return (
                f"✅ Got your *{doc_label}* — thank you!\n\n"
                f"📋 Still needed:\n{remaining_list}\n\n"
                f"Please send them one at a time when you're ready. 😊"
            )
        else:
            return (
                f"✅ Got your *{doc_label}*.\n\n"
                f"🎉 That's everything! All your documents have been received.\n\n"
                f"A consultant will review your profile and reach out to you shortly. "
                f"We'll be in touch soon! 🌍📚"
            )

    except Exception as e:
        print(f"❌ Error in handle_document: {e}")
        return (
            "Sorry, something went wrong while saving your document. "
            "Please try again in a moment."
        )

    finally:
        db.close()