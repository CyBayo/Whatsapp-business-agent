from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from twilio.twiml.messaging_response import MessagingResponse

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "alive"}

@app.post("/webhook")
async def whatsapp_webhook(request: Request):
    form_data = await request.form()
    incoming_msg = form_data.get("Body", "")
    sender = form_data.get("From", "")

    print(f"Message from {sender}: {incoming_msg}")

    resp = MessagingResponse()
    resp.message(f"Hello! I received your message: {incoming_msg}")

    return PlainTextResponse(str(resp), media_type="application/xml")