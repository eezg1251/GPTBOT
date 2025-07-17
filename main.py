# main.py
import os
from fastapi import FastAPI, Request
import httpx
from openai import OpenAI
import langdetect

app = FastAPI()

# Tokens desde Fly.io
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
META_TOKEN = os.getenv("META_TOKEN")
META_PHONE_NUMBER_ID = os.getenv("META_PHONE_NUMBER_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# 🧠 Prompt base personalizado
base_prompt_es = """
Eres el asesor virtual de PAMPA ESTRATÉGICA 🧠, una consultora de Atacama y Coquimbo.

⚠️ Solo debes saludar una vez al inicio de la conversación. En los siguientes mensajes, responde directamente sin saludar nuevamente.

Debes:
- Responder en español si el mensaje está en español, o en inglés si está en inglés. No mezcles idiomas en una misma respuesta.
- Entender frases informales como "cuánto cobran", "me ayudan con ferias", o "diseño bonito".
- Detectar cuando una consulta requiere atención humana, y responder:
"Este caso requiere un análisis más profundo. Escríbenos a contacto@pampaestrategica.cl o directamente al WhatsApp de Esteban Zepeda: +56942342276. También puedes agendar en www.pampaestrategica.cl."

🌟 Información Clave:
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

🤖 Preguntas frecuentes que puedes responder:
- "¿Cuánto cuesta el plan premium?"
- "¿Me ayudan con ventas en ferias?"
- "¿Qué incluye la asesoría legal?"
- "¿Diseñan logos?"
- "¿Puedo contratar solo redes sociales?"
- "¿Cuánto se demoran en entregar propuestas?"
- "¿Trabajan con emprendimientos sociales?"
"""

base_prompt_en = """
You are the AI advisor for PAMPA ESTRATÉGICA 🧠, a consulting firm based in Atacama and Coquimbo.

⚠️ Only greet in the first interaction. On follow-up messages, reply directly.

You must:
- Reply only in English when the message is in English (don't mix languages).
- Understand informal phrases like "how much is it?", "do you help with branding?", or "can you manage my social media?"
- When the case is specific or complex, respond with:
"This case requires a deeper analysis. Please email us at contacto@pampaestrategica.cl or write directly to Esteban Zepeda on WhatsApp: +56942342276. You can also book a meeting at www.pampaestrategica.cl."

🌟 Services:
- Branding and positioning
- Legal support
- Communication and sales strategies
- Cost optimization using technology

📦 Service Plans:
1. Essential Plan (CLP $400,000 - $600,000): basic branding, legal advice, distribution and cost diagnosis.
2. Integral Plan (CLP $700,000 - $1,000,000): full branding, legal strategy, CRM, communication and sales (3% commission).
3. Premium Plan (CLP $1,200,000 - $1,800,000): advanced branding, full legal support, CRM + sales + commercial coaching (5% commission).

📈 Key Benefits:
- Build distribution networks
- Measurable sales
- Reduce operational costs
- Scalable, sustainable growth
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

        # Detectar idioma
        try:
            detected_lang = langdetect.detect(text)
        except:
            detected_lang = "es"

        # Seleccionar prompt según idioma
        system_prompt = base_prompt_en if detected_lang == "en" else base_prompt_es

        # Respuesta de OpenAI
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ]
        )
        reply = response.choices[0].message.content.strip()

        # Enviar mensaje a WhatsApp
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
