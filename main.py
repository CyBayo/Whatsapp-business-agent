import os
import json
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv
from groq import Groq
from twilio.rest import Client as TwilioClient
from orders import get_orders, cancel_order

load_dotenv()

app = FastAPI()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
twilio_client = TwilioClient(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
OWNER_NUMBER = os.getenv("OWNER_WHATSAPP_NUMBER")
TWILIO_SANDBOX_NUMBER = "whatsapp:+14155238886"

conversations = {}

SYSTEM_PROMPT = (
    "You are a friendly assistant for a small business, chatting with customers on WhatsApp. "
    "Keep replies short, warm and conversational (under 300 characters). "
    "For anything about orders, ALWAYS use the get_my_orders tool and only state facts it returns. "
    "Never guess or invent order details. "
    "You must NEVER handle payments yourself: never give bank details or account numbers, "
    "never confirm that a payment was received, and never say an order is paid unless the tool data says so. "
    "If the customer wants to pay, says they have paid, or asks about payment, prices or refunds: "
    "first call get_my_orders, then call notify_owner with the reason and the order_id, "
    "then tell the customer the owner will follow up. "
    "NEVER say you have notified or contacted the owner unless you actually called notify_owner in this turn. "
    "If the customer clearly asks to cancel an order, call cancel_order. "
    "You can only cancel unpaid orders; if the order is already paid, call notify_owner instead. "
    "If it is unclear which order they mean, ask. "
    "Never claim to have done something you have no tool for."
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_my_orders",
            "description": "Get the current customer's orders, including status, payment status and delivery details.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "notify_owner",
            "description": "Alert the business owner. Use whenever payment is involved or a human is needed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {"type": "string", "description": "Short summary of what the customer needs."},
                    "order_id": {"type": "string", "description": "The related order ID, if any."},
                },
                "required": ["reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_order",
            "description": "Cancel one of the customer's unpaid orders.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "The order ID to cancel, e.g. ORD-1001."},
                },
                "required": ["order_id"],
            },
        },
    },
]

# Safety net: if a message contains any of these, the owner is ALWAYS alerted.
PAYMENT_WORDS = [
    "pay", "paid", "payment", "transfer", "account number", "bank",
    "refund", "receipt", "invoice", "price", "how much", "cost",
]


def looks_like_payment(text):
    text = text.lower()
    return any(word in text for word in PAYMENT_WORDS)


def notify_owner(customer_id, reason, order_id=None):
    alert = f"[{datetime.now():%Y-%m-%d %H:%M}] {customer_id} | order: {order_id or 'n/a'} | {reason}"
    print(f"OWNER ALERT: {alert}")
    with open("owner_alerts.txt", "a", encoding="utf-8") as f:
        f.write(alert + "\n")

    if OWNER_NUMBER:
        try:
            twilio_client.messages.create(
                from_=TWILIO_SANDBOX_NUMBER,
                to=OWNER_NUMBER,
                body=f"🔔 Customer alert\nFrom: {customer_id}\nOrder: {order_id or 'n/a'}\n{reason}",
            )
            print("Owner notified via WhatsApp.")
        except Exception as e:
            print(f"Failed to WhatsApp the owner: {e}")

    return {"status": "owner_notified"}

def run_tool(name, customer_id, args):
    if name == "get_my_orders":
        return get_orders(customer_id)
    if name == "notify_owner":
        return notify_owner(customer_id, args.get("reason", ""), args.get("order_id"))
    if name == "cancel_order":
        return cancel_order(customer_id, args.get("order_id", ""))
    return {"error": f"Unknown tool: {name}"}


def run_agent(history, customer_id, max_steps=5):
    tools_used = set()
    for _ in range(max_steps):
        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=history,
            tools=TOOLS,
        )
        msg = response.choices[0].message

        if not msg.tool_calls:
            reply = msg.content or "Sorry, I couldn't come up with a reply. Please try again!"
            return reply, tools_used

        history.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in msg.tool_calls
            ],
        })
        for tc in msg.tool_calls:
            print(f"Tool called: {tc.function.name}")
            tools_used.add(tc.function.name)
            args = json.loads(tc.function.arguments or "{}")
            result = run_tool(tc.function.name, customer_id, args)
            history.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result),
            })

    return "Sorry, I'm having trouble with that right now. Please try again in a moment!", tools_used


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

    tools_used = set()
    try:
        reply_text, tools_used = run_agent(history, sender)
        reply_text = reply_text[:1500]
    except Exception as e:
        print(f"Agent error: {e}")
        reply_text = "Sorry, something went wrong on my end. Please try again in a moment!"

    # Guardrail: payment-related message but the model didn't alert the owner
    if looks_like_payment(incoming_msg) and "notify_owner" not in tools_used:
        unpaid = [o["order_id"] for o in get_orders(sender) if o["payment_status"] == "unpaid"]
        notify_owner(sender, f"Auto-flagged payment message: {incoming_msg}", ", ".join(unpaid) or None)

    print(f"Reply: {reply_text}")

    history.append({"role": "assistant", "content": reply_text})
    conversations[sender] = history

    resp = MessagingResponse()
    resp.message(reply_text)

    return PlainTextResponse(str(resp), media_type="application/xml")