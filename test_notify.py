import sys
sys.path.append(".")

from app.services.escalate import notify_consultant

notify_consultant(
    phone="whatsapp:+2349075057294",  # the consultant's real number
    reason="Test alert from debug script",
    student_data={
        "full_name": "Test Student",
        "destination_country": "UK",
        "course_of_interest": "Computer Science",
        "budget": "£15,000/year",
        "qualifications": "BSc",
        "ielts_score": "6.5",
        "pipeline_stage": "qualified"
    }
)