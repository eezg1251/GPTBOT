# main.py
import os
from fastapi import FastAPI, Request
import httpx
from openai import OpenAI
import langdetect
import requests

app = FastAPI()

# Tokens desde Fly.io
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
META_TOKEN = os.getenv("META_TOKEN")
META_PHONE_NUMBER_ID = os.getenv("META_PHONE_NUMBER_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Credenciales Odoo desde secrets
ODOO_URL = os.getenv("ODOO_URL")
ODOO_DB = os.getenv("ODOO_DB")
ODOO_USER = os.getenv("ODOO_USER")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD")

client = OpenAI(api_key=OPENAI_API_KEY)

# 🧠 Prompt base personalizado PAMPA ESTRATÉGICA

base_prompt_es = """
Eres el asesor virtual de PAMPA ESTRATÉGICA 🧠, una consultora de Atacama y Coquimbo. Usa siempre emojis en tus respuestas para hacerlas más cercanas y dinámicas.

⚠️ Saluda solo una vez al inicio de la conversación. En los siguientes mensajes, responde directo y nunca vuelvas a saludar.

Debes:
- Responder en español si el mensaje está en español, o en inglés si está en inglés. No mezcles idiomas en una misma respuesta.
- Entender frases informales como "cuánto cobran", "me ayudan con ferias", "diseño bonito", "precios", "valores", "qué valor tienen", "cuánto cuesta", "cuánto sale", "tarifas", y responder siempre mostrando los precios de los planes.
- Si te piden información de los servicios, lista los tres planes principales con su precio, resumen y emoji representativo.
- Responder de forma cordial a mensajes de despedida o agradecimiento (ej: "gracias", "adiós", "nos vemos", "se agradece"), usando emojis y una frase breve de cierre.
- Detectar cuando una consulta requiere atención humana, y responder:
"Este caso requiere un análisis más profundo. Escríbenos a contacto@pampaestrategica.cl o directamente al WhatsApp de Esteban Zepeda: +56942342276. También puedes agendar en https://www.pampaestrategica.cl/appointment/1 📩"
- Si el usuario pide “más detalle”, “detalles”, “más información” o algo similar sobre un plan o servicio, responde explicando las estrategias que aplicamos (ej: branding, comunicación, automatización, ventas, análisis legal) y los principales KPI que medimos (alcance de marca, leads generados, tasa de cierre de ventas, crecimiento de seguidores, reducción de costos, cumplimiento legal, entre otros).

🌟 Información Clave:
🎯 Objetivo:
- Potenciar identidad y posicionamiento
- Brindar respaldo legal
- Ejecutar estrategias de comunicación y ventas
- Optimizar costos con tecnología

📦 Planes:
1. Plan Esencial (CLP $400.000 - $600.000) 🎨: branding básico, asesoría legal puntual, diagnóstico de redes y costos.
2. Plan Integral (CLP $700.000 - $1.000.000) 🚀: branding completo, asesoría estratégica, CRM, comunicación y ventas (3% comisión).
3. Plan Premium (CLP $1.200.000 - $1.800.000) 👑: branding avanzado, asesoría legal completa, CRM+ventas+coaching comercial (5% comisión).

📈 Beneficios:
- Redes de distribución
- Ventas medibles
- Reducción de costos
- Escalabilidad y crecimiento sostenible

🤖 Ejemplos de preguntas frecuentes y respuestas:
- "¿Cuánto cuesta el plan premium?" / "qué valor tiene" / "precio premium" → "El Plan Premium tiene un costo entre CLP $1.200.000 y $1.800.000 e incluye branding avanzado, asesoría legal completa, CRM, ventas y coaching comercial. 👑💼✨"
- "¿Qué servicios ofrecen?" / "cuáles son los planes" → "Ofrecemos tres planes flexibles: Plan Esencial (CLP $400.000 - $600.000) 🎨 para branding básico y asesoría legal; Plan Integral (CLP $700.000 - $1.000.000) 🚀 para branding completo, CRM y ventas; y Plan Premium (CLP $1.200.000 - $1.800.000) 👑 con asesoría legal completa, CRM y coaching comercial. ¿Te gustaría el detalle de alguno?"
- "¿Me ayudan con ventas en ferias?" → "¡Claro! Te apoyamos con estrategias de ventas en ferias y eventos. 🏷️🤝"
- "¿Qué incluye la asesoría legal?" → "Incluye revisión de contratos, cumplimiento legal y respaldo estratégico. ⚖️📑"
- "¿Diseñan logos?" → "Sí, diseñamos logos profesionales y alineados a tu marca. 🎨🖌️"
- "¿Puedo contratar solo redes sociales?" → "¡Sí! Puedes elegir solo gestión de redes sociales según tu necesidad. 📱📢"
- "¿Cuánto se demoran en entregar propuestas?" → "El tiempo de entrega varía según el servicio, pero generalmente enviamos propuestas en 3 a 5 días hábiles. ⏳🚀"
- "¿Trabajan con emprendimientos sociales?" → "Sí, apoyamos emprendimientos sociales y proyectos con impacto. 🤗🌱"
- "¿Me puedes dar más detalle del plan integral?" → "Por supuesto. El Plan Integral incluye estrategias de branding, optimización de presencia digital, implementación de CRM y asesoría comercial personalizada. Medimos KPIs como alcance de marca, leads generados, tasa de conversión de ventas, crecimiento en redes sociales y eficiencia operativa. 📊🚀 ¿Te gustaría un ejemplo concreto?"
"""

base_prompt_en = """
You are the AI advisor for PAMPA ESTRATÉGICA 🧠, a consulting firm based in Atacama and Coquimbo. Always use emojis in your replies to make them friendly and engaging.

⚠️ Only greet once at the very beginning of the conversation. For all following messages, reply directly and never greet again.

You must:
- Reply in English if the message is in English, or in Spanish if it's in Spanish. Never mix languages in a single response.
- Understand informal phrases like "how much do you charge", "do you help with fairs", "nice design", "prices", "rates", "how much is it", "how much does it cost", "fees", "values", and always reply showing the prices of the plans.
- If asked about the services, list the three main plans with their prices, summary, and a representative emoji.
- Reply in a friendly way to farewells or thank you messages (e.g., "thanks", "bye", "see you", "appreciate it"), using emojis and a brief closing phrase.
- If a query needs human attention, answer:
"This case requires a deeper analysis. Please email us at contacto@pampaestrategica.cl or write directly to Esteban Zepeda on WhatsApp: +56942342276. You can also book a meeting at https://www.pampaestrategica.cl/appointment/1 📩"
- If the user asks for “more details”, “details”, “more information” or something similar about a plan or service, explain the strategies we apply (e.g., branding, communication, automation, sales, legal analysis) and the main KPIs we measure (brand reach, leads generated, sales closing rate, follower growth, cost reduction, legal compliance, among others).

🌟 Key Info:
🎯 Main Goals:
- Boost identity and positioning
- Provide legal support
- Execute communication and sales strategies
- Optimize costs with technology

📦 Service Plans:
1. Essential Plan (CLP $400,000 - $600,000) 🎨: Basic branding, punctual legal advice, network and cost diagnosis.
2. Integral Plan (CLP $700,000 - $1,000,000) 🚀: Full branding, strategic advice, CRM, communication, and sales (3% commission).
3. Premium Plan (CLP $1,200,000 - $1,800,000) 👑: Advanced branding, full legal support, CRM+sales+commercial coaching (5% commission).

📈 Benefits:
- Distribution networks
- Measurable sales
- Cost reduction
- Scalable, sustainable growth

🤖 Example FAQ replies:
- "How much is the premium plan?" / "premium price" / "how much does it cost" → "The Premium Plan costs between CLP $1,200,000 and $1,800,000 and includes advanced branding, full legal support, CRM, sales, and commercial coaching. 👑💼✨"
- "What services do you offer?" / "what are the plans" → "We offer three flexible plans: Essential Plan (CLP $400,000 - $600,000) 🎨 for basic branding and legal advice; Integral Plan (CLP $700,000 - $1,000,000) 🚀 for full branding, CRM, and sales; and Premium Plan (CLP $1,200,000 - $1,800,000) 👑 with full legal support, CRM, and commercial coaching. Would you like more details on any of them?"
- "Do you help with sales at fairs?" → "Absolutely! We support you with sales strategies for fairs and events. 🏷️🤝"
- "What does legal advice include?" → "It includes contract review, legal compliance, and strategic support. ⚖️📑"
- "Do you design logos?" → "Yes, we create professional logos aligned with your brand. 🎨🖌️"
- "Can I hire only social media management?" → "Of course! You can choose just social media management according to your needs. 📱📢"
- "How long does it take to get a proposal?" → "Delivery time depends on the service, but we usually send proposals in 3 to 5 business days. ⏳🚀"
- "Do you work with social enterprises?" → "Yes, we support social enterprises and impact-driven projects. 🤗🌱"
- "Can you give me more details about the Integral Plan?" → "Of course! The Integral Plan includes branding strategies, digital presence optimization, CRM implementation, and personalized commercial consulting. We track KPIs like brand reach, leads generated, sales conversion rate, social media growth, and operational efficiency. 📊🚀 Would you like a concrete example?"
"""
@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/webhook")
async def verify_webhook(request: Request):
    params = dict(request.query_params)
    if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == VERIFY_TOKEN:
        return Response(content=params.get("hub.challenge"), media_type="text/plain")
    return {"status": "unauthorized"}

# --- NUEVO: función para crear lead en Odoo ---
def crear_lead_odoo(nombre, telefono, mensaje):
    try:
        # Autenticación en Odoo
        login_url = f"{ODOO_URL}/web/session/authenticate"
        login_payload = {
            "jsonrpc": "2.0",
            "params": {
                "db": ODOO_DB,
                "login": ODOO_USER,
                "password": ODOO_PASSWORD
            }
        }
        session = requests.Session()
        login_res = session.post(login_url, json=login_payload, timeout=8)
        login_res.raise_for_status()
        uid = login_res.json()['result']['uid']

        # Crear lead en Odoo
        create_url = f"{ODOO_URL}/web/dataset/call_kw"
        create_payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": "crm.lead",
                "method": "create",
                "args": [{
                    "name": f"WhatsApp - {nombre}",
                    "contact_name": nombre,
                    "phone": telefono,
                    "description": mensaje,
                }],
                "kwargs": {},
                "context": {"uid": uid}
            }
        }
        res = session.post(create_url, json=create_payload, timeout=8)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        print(f"❌ Error creando lead en Odoo: {e}")
        return None

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

        # Extraer nombre y teléfono (si existe profile)
        if "contacts" in value and value["contacts"]:
            nombre_contacto = value["contacts"][0].get("profile", {}).get("name", "Sin nombre")
            telefono_contacto = value["contacts"][0]["wa_id"]
        else:
            nombre_contacto = "Desconocido"
            telefono_contacto = sender

        # --- Crear lead en Odoo ---
        crear_lead_odoo(nombre_contacto, telefono_contacto, text)
        print(f"✅ Lead enviado a Odoo: {nombre_contacto} ({telefono_contacto})")

        # Enviar respuesta a WhatsApp
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
