# main.py
import os
from fastapi import FastAPI, Request
import httpx
from openai import OpenAI

app = FastAPI()

# Variables de entorno
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
META_TOKEN = os.getenv("META_TOKEN")
META_PHONE_NUMBER_ID = os.getenv("META_PHONE_NUMBER_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Cliente de OpenAI
openai_client = OpenAI(api_key=OPENAI_API_KEY)

@app.get("/")
def root():
    return {"message": "Servidor de WhatsApp IA activo 🚀"}

@app.get("/webhook")
async def verify_webhook(request: Request):
    params = dict(request.query_params)
    if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == VERIFY_TOKEN:
        return int(params.get("hub.challenge"))
    return {"status": "unauthorized"}

@app.post("/webhook")
async def receive_message(request: Request):
    body = await request.json()
    print("🔔 Webhook recibido:", body)

    try:
        entry = body["entry"][0]
        change = entry["changes"][0]["value"]

        if "messages" not in change:
            print("📭 No hay mensajes nuevos. Solo estado de entrega.")
            return {"status": "ok"}

        message = change["messages"][0]
        text = message["text"]["body"]
        sender = message["from"]

        # 🧠 Obtener respuesta de OpenAI
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": text}]
        )
        reply = response.choices[0].message.content.strip()

        # 📤 Enviar respuesta a WhatsApp
        url = f"https://graph.facebook.com/v19.0/{META_PHONE_NUMBER_ID}/messages"
        headers = {
            "Authorization": f"Bearer {META_TOKEN}",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": sender,
            "type": "text",
            "text": {"body": reply}
        }

        async with httpx.AsyncClient() as http_client:
            r = await http_client.post(url, headers=headers, json=payload)
            print("✅ WhatsApp enviado:", r.status_code, r.text)

    except Exception as e:
        print("❌ Error en el webhook:", e)

    return {"status": "ok"}
