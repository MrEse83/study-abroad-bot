from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.ai_agent import get_agent_response, clear_memory
from app.services.notifications import trigger_n8n_notification
from twilio.twiml.messaging_response import MessagingResponse

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp"])


@router.post("/webhook")
async def whatsapp_webhook(
    request: Request,
    From: str = Form(...),
    Body: str = Form(...),
    db: Session = Depends(get_db)
):
    patient_phone = From
    patient_message = Body.strip()

    print(f"Message from {patient_phone}: {patient_message}")

    twiml = MessagingResponse()

    try:
        reply = get_agent_response(
            message=patient_message,
            phone=patient_phone,
            db=db
        )

        
        if "confirmed" in reply.lower() and "appointment" in reply.lower():
            await trigger_n8n_notification({
                "phone": patient_phone.replace("whatsapp:", ""),
                "message": reply,
                "source": "whatsapp"
            })

        twiml.message(reply)

    except Exception as e:
        print(f"Error processing message: {e}")
        twiml.message(
            "Sorry, I'm having trouble right now. Please try again in a moment."
        )

    return Response(content=str(twiml), media_type="application/xml")


@router.post("/reset/{phone}")
def reset_conversation(phone: str):
    clear_memory(f"whatsapp:{phone}")
    return {"message": f"Conversation reset for {phone}"}