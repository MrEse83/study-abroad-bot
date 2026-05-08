from fastapi import APIRouter, Form, Request
from fastapi.responses import Response
from app.services.ai_agent import get_agent_response, clear_memory
from app.services.doc_handler import handle_document
from twilio.twiml.messaging_response import MessagingResponse
from typing import Optional

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp"])


@router.post("/webhook")
async def whatsapp_webhook(
    request: Request,
    From: str = Form(...),
    Body: str = Form(default=""),
    NumMedia: int = Form(default=0),
    MediaUrl0: Optional[str] = Form(default=None),
    MediaContentType0: Optional[str] = Form(default=None),
):
    student_phone = From
    student_message = Body.strip()

    print(f"📩 Message from {student_phone}: {student_message}")
    if NumMedia > 0:
        print(f"📎 Media received: {MediaContentType0} — {MediaUrl0}")

    twiml = MessagingResponse()

    try:
        if NumMedia > 0 and MediaUrl0:
            # ✅ Fixed: no db arg needed — handle_document manages its own session
            reply = handle_document(
                phone=student_phone,
                media_url=MediaUrl0,
                media_type=MediaContentType0
            )
        else:
            reply = get_agent_response(
                message=student_message,
                phone=student_phone
            )

        twiml.message(reply)

    except Exception as e:
        print(f"❌ Error processing message from {student_phone}: {e}")
        twiml.message(
            "Sorry, I'm having trouble right now. Please try again in a moment. 🙏"
        )

    return Response(content=str(twiml), media_type="application/xml")


@router.post("/reset/{phone}")
def reset_conversation(phone: str):
    """Reset conversation memory for a student (useful for testing)."""
    clear_memory(phone)
    clear_memory(f"whatsapp:{phone}")
    clear_memory(f"whatsapp:+{phone}")
    return {"message": f"Conversation reset for {phone}"}