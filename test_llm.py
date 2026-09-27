import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    ai_response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"Respond conversationally and concisely (under 300 characters) to this WhatsApp message: {incoming_msg}"
    )
    reply_text = ai_response.text[:1500]  # safety cap under Twilio's 1600 limit


