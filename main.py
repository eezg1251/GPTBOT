# main.py
import os
from fastapi import FastAPI, Request
import httpx
from openai import OpenAI

app = FastAPI()

# Tokens desde Fly.io
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
META_TOKEN = os.getenv("META_TOKEN")
META_PHONE_NUMBER_ID = os.getenv("META_PHONE_NUMBER_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# 🧠 Prompt personalizado con información de Pampa Estratégica y lenguaje informal/multilenguaje
system_prompt = """
You are the virtual advisor for PAMPA ESTRATÉGICA 🧠, a consulting firm based in Atacama and Coquimbo.

Start every conversation with:
"Hola 👋, soy el asesor IA de PAMPA ESTRATÉGICA. ¿En qué te puedo ayudar hoy?"

You must:
- Answer questions in both Spanish and English.
- Understand informal phrases like "cuánto cobran", "me ayudan con ferias", or "diseño bonito".
- Detect when a message requires human follow-up and suggest:
  "Este caso requiere un análisis más profundo. Escríbenos a contacto@pampaestrategica.cl o directamente al WhatsApp de Esteban Zepeda: +56942342276. También puedes agendar en www.pampaestrategica.cl."

🌟 Key Information:

🎯 Objetivo:
- Potenciar identidad y posicionamiento
- Brindar respaldo legal
- Ejecutar estrategias de comunicación y ventas
- Optimizar costos con tecnología

📦 Planes:
1. Plan Esencial (CLP $400.000 - $600.000): branding básico, asesoría legal puntual, diagnóstico de redes y costos.
2. Plan Integral (CLP $700.000 - $1.000.000): branding completo, asesoría estratégica, CRM, comunicación y ventas (3% comisión).
3. Plan Premium (CLP $1.200.000 - $1.800.000): branding avanzado, asesoría legal completa, CRM+ventas+coaching comercial (5% comisión).

📈 Beneficios:
- Redes de distribución
- Ventas medibles
- Reducción de costos
- Escalabilidad y crecimiento sostenible

🚀 Ejemplos de preguntas que puedes responder:
- "Cuánto cuesta el plan premium?"
- "Me ayudan con ventas en ferias?"
- "Qué incluye la asesoría legal?"
- "Do you work with startups?"
- "How much is the essential plan?"

Always be clear, friendly and professional.
"""

@app.get("/")
def root():
    return {"status": "ok"}

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
        value = entry["changes"][0]["value"]

        if "messages" not in value:
            print("📬 No hay mensajes nuevos. Solo estado de entrega.")
            return {"status": "ok"}

        message = value["messages"][0]
        text = message["text"]["body"]
        sender = message["from"]

        # 🧠 Obtener respuesta desde OpenAI
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ]
        )
        reply = response.choices[0].message.content.strip()

        # 📤 Enviar respuesta por WhatsApp
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
