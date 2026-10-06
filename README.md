# WhatsApp Business Agent

A conversational AI agent for WhatsApp that helps a small business talk to customers, check on orders, and hand off anything involving money to a human owner — built end-to-end with Python, an LLM, and real tool use.

**Live demo:** message `join twilio-trial` to **+1 (737) 250-8034** on WhatsApp, then start chatting (sandbox access required — see [Try it yourself](#try-it-yourself)).

## Why this project

Most "WhatsApp chatbot" demos stop at FAQ-style replies. This one is an actual agent: it holds a real conversation, calls tools to look up live order data instead of guessing, takes real actions (cancelling an order), and — critically — knows where its own authority ends. It never touches payments. The moment money comes up, it stops acting on its own and alerts a human.

## What it does

- Chats naturally about anything, not just scripted replies
- Looks up a customer's real orders (status, payment, delivery date) via a tool call — never invents order details
- Cancels unpaid orders on request
- Refuses to cancel paid orders, and refuses to share payment/bank details, under any phrasing
- Escalates anything payment-related to the business owner, who gets a real WhatsApp alert
- Remembers each customer's conversation across sessions, even after the server restarts
- Runs as a deployed, always-on service — not dependent on anyone's laptop being on

## How it works

```
Customer on WhatsApp
        │
        ▼
   Twilio (WhatsApp API)
        │  webhook
        ▼
   FastAPI server  ──────►  Groq (LLM + tool calling)
        │                         │
        │                         ├─ get_my_orders   → orders.py (mock DB)
        │                         ├─ cancel_order     → orders.py (mock DB)
        │                         └─ notify_owner     → Twilio REST API → owner's WhatsApp
        │
        ▼
   Upstash Redis (per-customer conversation history)
```

The LLM decides *when* to call a tool; the code decides *what the tool is allowed to do*. A code-level guardrail also scans every incoming message for payment-related language and force-alerts the owner if the model fails to — so the safety behavior doesn't depend entirely on the model getting it right every time.

## Tech stack

| Piece | Tool | Why |
|---|---|---|
| Messaging channel | Twilio WhatsApp Sandbox | No business verification needed to prototype |
| Backend | FastAPI | Async, simple webhook handling |
| LLM + tool calling | Groq (`openai/gpt-oss-20b`) | Fast, generous free tier, OpenAI-compatible tool-calling format |
| Conversation memory | Upstash Redis (REST API) | Serverless, survives restarts/cold starts, no extra infra to manage |
| Hosting | Render | Free tier, auto-deploys from GitHub on push |

## Project structure

```
main.py         # FastAPI app, webhook, agent loop, tool definitions, owner alerting
orders.py       # Mock orders "database" and order logic (lookup, cancel)
requirements.txt
.env            # Secrets (not committed — see below)
```

## Running it yourself

1. Clone the repo and create a virtual environment
2. `pip install -r requirements.txt`
3. Create a `.env` file with:
   ```
   TWILIO_ACCOUNT_SID=
   TWILIO_AUTH_TOKEN=
   GROQ_API_KEY=
   OWNER_WHATSAPP_NUMBER=whatsapp:+<number>
   UPSTASH_REDIS_REST_URL=
   UPSTASH_REDIS_REST_TOKEN=
   ```
4. `uvicorn main:app --reload`
5. Expose it with `ngrok http 8000` and point your Twilio sandbox webhook at `<ngrok-url>/webhook`

## Try it yourself

1. On WhatsApp, message **+1 (737) 250-8034** with `join twilio-trial`
2. Once confirmed, try asking about an order, or say "I want to pay" and watch it hand off instead of pretending to process anything

## What I'd build next

- A real database instead of a hardcoded mock order list
- Multi-language support (Pidgin, Yoruba, Hausa)
- An owner-facing dashboard for pending escalations
- Proactive check-ins on orders, instead of only responding when messaged

## What I learned

Getting from "a bootcamp certificate" to a working, deployed agent meant debugging across the whole stack: git and environment setup, a Meta Business verification dead end that pushed me to Twilio instead, three different LLM providers before landing on one with a stable free tier, webhook timeout and character-limit edge cases, and finally making conversation state survive a server restart. The hardest and most valuable part wasn't the AI call — it was everything around it that makes an AI feature actually reliable.
