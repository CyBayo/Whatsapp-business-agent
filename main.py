import os
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

app = FastAPI()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Stores conversation history per customer
conversations = {}

@app.get("/")
def read_root():
    return {"status": "alive"}

@app.post("/webhook")
async def whatsapp_webhook(request: Request):
    form_data = await request.form()
    incoming_msg = form_data.get("Body", "")
    sender = form_data.get("From", "")

    print(f"Message from {sender}: {incoming_msg}")

    # Get this customer's history, or start a new one
    history = conversations.get(sender, [
        {"role": "system", "content": "You are a friendly business assistant chatting on WhatsApp. Keep replies conversational and under 300 characters."}
    ])

    history.append({"role": "user", "content": incoming_msg})

    chat_completion = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=history
    )
    reply_text = chat_completion.choices[0].message.content[:1500]

    history.append({"role": "assistant", "content": reply_text})
    conversations[sender] = history

    resp = MessagingResponse()
    resp.message(reply_text)

    return PlainTextResponse(str(resp), media_type="application/xml")
