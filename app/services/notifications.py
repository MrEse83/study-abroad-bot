import httpx
from app.config import N8N_WEBHOOK_URL


async def trigger_n8n_notification(appointment_data: dict):
    """
    Fires a webhook to Make.com (or n8n) after a successful booking.
    Handles: WhatsApp to patient, WhatsApp to doctor, email.
    """
    if not N8N_WEBHOOK_URL:
        print("WEBHOOK_URL not set — skipping notification")
        return

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                N8N_WEBHOOK_URL,
                json=appointment_data,
                timeout=15
            )
            print(f"Notification webhook fired: {response.status_code}")
        except httpx.ConnectError:
            print("Notification webhook failed: could not connect")
        except httpx.TimeoutException:
            print("Notification webhook failed: timeout")
        except Exception as e:
            print(f"Notification webhook failed: {e}")