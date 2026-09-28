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

SYSTEM_PROMPT = "You are a friendly business assistant chatting on WhatsApp. Keep replies conversational and under 300 characters."


@app.get("/")
def read_root():
    return {"status": "alive"}


@app.post("/webhook")
async def whatsapp_webhook(request: Request):
    form_data = await request.form()
    incoming_msg = form_data.get("Body", "")
    sender = form_data.get("From", "")

    print(f"Message from {sender}: {incoming_msg}")

    history = conversations.get(sender, [{"role": "system", "content": SYSTEM_PROMPT}])
    history.append({"role": "user", "content": incoming_msg})

    chat_completion = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=history
    )

    raw_reply = chat_completion.choices[0].message.content
    print(f"Raw reply: {repr(raw_reply)}")

    reply_text = (raw_reply or "Sorry, I couldn't come up with a reply. Please try again!")[:1500]

    history.append({"role": "assistant", "content": reply_text})
    conversations[sender] = history

    resp = MessagingResponse()
    resp.message(reply_text)

    return PlainTextResponse(str(resp), media_type="application/xml")