import os
import requests
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse

app = FastAPI()

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
META_TOKEN = os.getenv("META_TOKEN")
PHONE_NUMBER_ID = os.getenv("META_PHONE_NUMBER_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_MODEL = "gpt-3.5-turbo"  # o "gpt-3.5-turbo"

@app.get("/webhook")
async def verify_webhook(request: Request):
    params = dict(request.query_params)
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return PlainTextResponse(content=challenge, status_code=200)
    return PlainTextResponse(content="Token de verificación inválido", status_code=403)

@app.post("/webhook")
async def receive_message(request: Request):
    data = await request.json()
    try:
        message = data["entry"][0]["changes"][0]["value"]["messages"][0]
        from_number = message["from"]
        msg_body = message["text"]["body"]

        print(f"📩 Mensaje recibido: {msg_body} desde {from_number}")

        # Llama a OpenAI
        ai_reply = ask_gpt(msg_body)

        # Responde por WhatsApp
        send_whatsapp_message(from_number, ai_reply)

    except Exception as e:
        print("❌ Error procesando mensaje:", e)

    return {"status": "ok"}

def ask_gpt(user_message: str) -> str:
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "Eres un asistente profesional de WhatsApp de la consultora Pampa Estratégica. Responde de forma breve, amable y clara."
            },
            {
                "role": "user",
                "content": user_message
            }
        ]
    }
    try:
        response = requests.post(OPENAI_URL, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as ex:
        print("❌ Error al consultar OpenAI:", ex)
        return "¡Hola! Soy el asistente de Pampa Estratégica. ¿En qué puedo ayudarte?"

def send_whatsapp_message(recipient_id: str, text: str):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {META_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient_id,
        "type": "text",
        "text": {"body": text}
    }
    response = requests.post(url, headers=headers, json=payload)
    print("➡️ WhatsApp API status:", response.status_code)
    if response.status_code != 200:
        print("❌ Detalle:", response.text)
