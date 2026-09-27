import os
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv
from google import genai

load_dotenv()

app = FastAPI()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

@app.get("/")
def read_root():
    return {"status": "alive"}

@app.post("/webhook")
async def whatsapp_webhook(request: Request):
    form_data = await request.form()
    incoming_msg = form_data.get("Body", "")
    sender = form_data.get("From", "")

    print(f"Message from {sender}: {incoming_msg}")

    ai_response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=f"Respond conversationally and concisely (under 300 characters) to this WhatsApp message: {incoming_msg}"
    )
    reply_text = ai_response.text[:1500]

    resp = MessagingResponse()
    resp.message(reply_text)

    return PlainTextResponse(str(resp), media_type="application/xml")
