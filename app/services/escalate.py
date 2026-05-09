from twilio.rest import Client
from app.config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER
import os

# Consultant's WhatsApp number
CONSULTANT_NUMBER = "whatsapp:+2349075057294"

# Your app base URL — must be set in Railway Variables
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")


def notify_consultant(phone: str, reason: str, student_data: dict):
    """
    Send a WhatsApp alert to the consultant when a student needs human attention.
    """
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

        name = student_data.get("full_name") or "Unknown"
        country = student_data.get("destination_country") or "Not specified"
        course = student_data.get("course_of_interest") or "Not specified"
        budget = student_data.get("budget") or "Not specified"
        qualifications = student_data.get("qualifications") or "Not specified"
        ielts = student_data.get("ielts_score") or "Not taken"
        stage = student_data.get("pipeline_stage") or "new"

        # Clean phone for URL
        clean_phone = phone.replace("whatsapp:+", "").replace("whatsapp:", "").replace("+", "")

        # Plain URL — WhatsApp makes plain URLs clickable automatically
        profile_url = f"{BASE_URL}/dashboard/student/{clean_phone}"

        # Header based on stage
        if stage == "docs_received":
            header = "📁 *All Documents Received — Ready for Review*"
            urgency = "🟢"
        elif stage == "qualified":
            header = "✅ *Student Qualified — Needs Consultation*"
            urgency = "🟡"
        else:
            header = "🚨 *Student Needs Attention*"
            urgency = "🔴"

        message = (
            f"{header}\n\n"
            f"👤 *Name:* {name}\n"
            f"📱 *Phone:* {phone}\n"
            f"🌍 *Destination:* {country}\n"
            f"📚 *Course:* {course}\n"
            f"💰 *Budget:* {budget}\n"
            f"🎓 *Qualifications:* {qualifications}\n"
            f"📝 *IELTS:* {ielts}\n"
            f"📊 *Stage:* {stage}\n\n"
            f"{urgency} *Reason:* {reason}\n\n"
            f"🔗 View Full Profile & Documents:\n"
            f"{profile_url}\n\n"
            f"Please follow up with this student directly. 🙏"
        )

        client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            to=CONSULTANT_NUMBER,
            body=message
        )

        print(f"✅ Consultant notified about {phone} | Stage: {stage}")

    except Exception as e:
        print(f"❌ Failed to notify consultant: {e}")
        raise