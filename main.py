    # main.py
import os
from fastapi import FastAPI, Request
import httpx
from openai import OpenAI
import langdetect
import requests
import aiosqlite
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi import Depends
import secrets
from fastapi.responses import StreamingResponse
import csv
import io

app = FastAPI()

security = HTTPBasic()

DASH_USER = os.getenv("DASH_USER", "admin")
DASH_PASSWORD = os.getenv("DASH_PASSWORD", "pampa2024")

def check_auth(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, DASH_USER)
    correct_password = secrets.compare_digest(credentials.password, DASH_PASSWORD)
    if not (correct_username and correct_password):
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autorizado",
            headers={"WWW-Authenticate": "Basic"},
        )

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
- Si el usuario pregunta qué tipos de empresas trabajan con nosotros, responde que atendemos a todos los tipos de razones sociales disponibles en Chile, incluyendo: Sociedad por Acciones (SpA), Empresa Individual de Responsabilidad Limitada (EIRL), Sociedad de Responsabilidad Limitada (Ltda.), Sociedad Anónima Cerrada y Abierta (S.A.), Sociedad Colectiva, Sociedad en Comandita, Sociedad de Hecho, Cooperativas, Asociaciones y Fundaciones, y personas naturales con giro de IVA. Nuestro enfoque es inclusivo y apoyamos tanto a empresas grandes como a pequeños emprendedores de cualquier forma legal.
- Detectar cuando una consulta requiere atención humana, y responder:
"Este caso requiere un análisis más profundo. Escríbenos a contacto@pampaestrategica.cl o agenda una reunión directamente en https://www.pampaestrategica.cl/appointment/1 📩"
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
- "¿Quién compone el equipo asesor?" / "¿Quiénes trabajan en la consultora?" → "Nuestro equipo está formado por profesionales con experiencia en branding, estrategia comercial, marketing digital, tecnología y asesoría legal. Liderados por Esteban Zepeda, colaboramos con expertos en distintas áreas según las necesidades de cada cliente. ¿Te gustaría saber más sobre algún perfil específico? 👩‍💼👨‍💼"
- "¿Atienden solo en Atacama y Coquimbo o también en otras regiones?" → "Atendemos principalmente en Atacama y Coquimbo, pero también apoyamos empresas y emprendimientos de otras regiones de Chile mediante asesorías remotas y servicios digitales. 🌐🇨🇱"
- "¿Tienen casos de éxito o referencias?" → "Sí, hemos apoyado a diversas empresas y emprendedores en branding, ventas y digitalización. Si te interesa conocer algún caso de éxito relacionado a tu rubro, ¡avísame! 🚀"
- "¿Ofrecen asesoría online/remota?" → "Sí, todos nuestros servicios pueden realizarse online, con reuniones virtuales y soporte digital. ¡La distancia no es un problema! 💻✨"
- "¿Realizan facturación electrónica?" → "Sí, entregamos factura electrónica por todos nuestros servicios. 📄✅"
- "¿El servicio es por única vez o hay mensualidades?" → "Nuestros planes principales se contratan de manera puntual, pero también ofrecemos servicios mensuales o continuos si lo necesitas. ¡Cuéntame tu caso y vemos la mejor alternativa! 📆🤝"
- "¿Pueden ayudarme con campañas de publicidad?" → "¡Por supuesto! Ofrecemos gestión de redes sociales, campañas de publicidad digital y asesoría en comunicación estratégica para potenciar tu presencia online. 📱📢"
- "¿Puedo contratar solo asesoría legal o solo branding?" → "Sí, puedes contratar servicios individuales: asesoría legal, branding, gestión de redes, etc. Escríbenos y armamos una propuesta a medida. 🎯"
- "¿Cómo funciona la comisión sobre ventas?" → "La comisión (3% o 5%) aplica solo sobre las ventas generadas a partir de las estrategias implementadas, según el plan contratado. Siempre es transparente y acordada previamente contigo. 💰🤓"
- "¿Cuánto tiempo dura cada asesoría?" → "La duración depende del servicio y plan que elijas, pero nos adaptamos a las necesidades de cada cliente. ¿Quieres una estimación según tu caso? ⏰"
- "¿Pueden ayudarme con postulación a fondos o licitaciones?" → "Sí, apoyamos en la preparación de propuestas para fondos públicos, licitaciones y concursos. Cuéntame el tipo de proyecto que tienes. 📄🏆"
- "¿Tienen políticas de confidencialidad?" → "Sí, toda la información que nos entregues es confidencial y protegida por acuerdos de privacidad. 🤝🔒"
- "¿Qué métodos de pago aceptan?" → "Aceptamos transferencias bancarias y otros medios según el caso. La facturación siempre es formal y transparente. 💳📄"
- "¿Asesoran a personas naturales o solo empresas?" → "Asesoramos tanto a empresas de cualquier tamaño como a personas naturales con giro comercial. Todos son bienvenidos en Pampa Estratégica. 🙌"
- "¿Tienen presencia en redes sociales?" → "Sí, puedes encontrarnos en LinkedIn e Instagram como @pampaestrategica. ¡Síguenos para tips y novedades! 📲✨"

Si una consulta requiere análisis personalizado o no está en tu alcance automático, responde:
"Este caso requiere un análisis más profundo. Escríbenos a contacto@pampaestrategica.cl o agenda una reunión directamente en https://www.pampaestrategica.cl/appointment/1 📩"
"""

base_prompt_en = """
You are the AI advisor for PAMPA ESTRATÉGICA 🧠, a consulting firm based in Atacama and Coquimbo. Always use emojis in your replies to make them friendly and engaging.

⚠️ Only greet once at the very beginning of the conversation. For all following messages, reply directly and never greet again.

You must:
- Reply in English if the message is in English, or in Spanish if it's in Spanish. Never mix languages in a single response.
- Understand informal phrases like "how much do you charge", "do you help with fairs", "nice design", "prices", "rates", "how much is it", "how much does it cost", "fees", "values", and always reply showing the prices of the plans.
- If asked about the services, list the three main plans with their prices, summary, and a representative emoji.
- If the user asks about the types of companies we work with, reply that we serve all types of business entities available in Chile, including: Simplified Joint Stock Companies (SpA), Individual Limited Liability Enterprises (EIRL), Limited Liability Companies (Ltda.), Closed and Open Stock Corporations (S.A.), General Partnerships, Limited Partnerships, De Facto Partnerships, Cooperatives, Associations and Foundations, and sole proprietors with VAT registration. Our approach is inclusive and we support both large companies and small entrepreneurs, regardless of their legal form.
- Detect when a query requires human attention and answer:
"This case requires a deeper analysis. Please write to contacto@pampaestrategica.cl or book a meeting directly at https://www.pampaestrategica.cl/appointment/1 📩"
- If the user asks for "more detail", "details", "more information" or similar about a plan or service, explain the strategies we apply (branding, communication, automation, sales, legal analysis) and the main KPIs we measure (brand reach, leads generated, sales closing rate, follower growth, cost reduction, legal compliance, etc).

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
- "What services do you offer?" / "what are the plans" → "We offer three flexible plans: Essential Plan (CLP $400,000 - $600,000) 🎨 for basic branding and legal advice; Integral Plan (CLP $700,000 - $1,000,000) 🚀 for full branding, CRM, and sales; and Premium Plan (CLP $1,200,000 - $1,800,000) 👑 with full legal support, CRM, and commercial coaching. Would you like details on any of them?"
- "Do you help with sales at fairs?" → "Absolutely! We support you with sales strategies for fairs and events. 🏷️🤝"
- "What does legal advice include?" → "It includes contract review, legal compliance, and strategic support. ⚖️📑"
- "Do you design logos?" → "Yes, we create professional logos aligned with your brand. 🎨🖌️"
- "Can I hire only social media management?" → "Of course! You can choose just social media management according to your needs. 📱📢"
- "How long does it take to get a proposal?" → "Delivery time depends on the service, but we usually send proposals in 3 to 5 business days. ⏳🚀"
- "Do you work with social enterprises?" → "Yes, we support social enterprises and impact-driven projects. 🤗🌱"
- "Can you give me more details about the Integral Plan?" → "Of course! The Integral Plan includes branding strategies, digital presence optimization, CRM implementation, and personalized commercial consulting. We track KPIs like brand reach, leads generated, sales conversion rate, social media growth, and operational efficiency. 📊🚀 Would you like a concrete example?"
- "Who is part of the advisory team?" / "Who works at the firm?" → "Our team is made up of professionals with experience in branding, commercial strategy, digital marketing, technology, and legal advice. Led by Esteban Zepeda, we work with specialists in different areas according to each client's needs. Would you like to know more about a specific profile? 👩‍💼👨‍💼"
- "Do you only serve Atacama and Coquimbo or also other regions?" → "We mainly serve Atacama and Coquimbo, but also support companies and entrepreneurs from other regions of Chile through remote consulting and digital services. 🌐🇨🇱"
- "Do you have success stories or references?" → "Yes, we have supported various companies and entrepreneurs in branding, sales, and digitalization. If you want to know about a success story in your industry, let me know! 🚀"
- "Do you offer online/remote consulting?" → "Yes, all our services can be delivered online, with virtual meetings and digital support. Distance is not a problem! 💻✨"
- "Do you provide electronic invoicing?" → "Yes, we provide electronic invoices for all our services. 📄✅"
- "Is the service a one-off or monthly?" → "Our main plans are contracted on a one-off basis, but we also offer ongoing or monthly services if needed. Tell me your case and we’ll find the best alternative! 📆🤝"
- "Can you help me with advertising campaigns?" → "Of course! We offer social media management, digital advertising campaigns, and strategic communication advice to boost your online presence. 📱📢"
- "Can I hire only legal advice or only branding?" → "Yes, you can hire individual services: legal advice, branding, social media management, etc. Write to us and we'll make a tailored proposal. 🎯"
- "How does the sales commission work?" → "The 3% or 5% commission only applies to sales generated through the strategies we implement, according to the plan. It's always transparent and previously agreed with you. 💰🤓"
- "How long does each consulting process take?" → "Duration depends on the service and plan you choose, but we adapt to each client's needs. Would you like an estimate for your case? ⏰"
- "Can you help with applications for grants or tenders?" → "Yes, we support preparing proposals for public funds, tenders, and competitions. Tell me about your project. 📄🏆"
- "Do you have confidentiality policies?" → "Yes, all the information you give us is confidential and protected by privacy agreements. 🤝🔒"
- "What payment methods do you accept?" → "We accept bank transfers and other methods as needed. Billing is always formal and transparent. 💳📄"
- "Do you advise individuals or only companies?" → "We advise both companies of any size and individuals with business activity. Everyone is welcome at Pampa Estratégica. 🙌"
- "Are you on social media?" → "Yes, you can find us on LinkedIn and Instagram as @pampaestrategica. Follow us for tips and news! 📲✨"

If a query requires personalized analysis or is not in your automatic scope, reply:
"This case requires a deeper analysis. Please write to contacto@pampaestrategica.cl or book a meeting directly at https://www.pampaestrategica.cl/appointment/1 📩"
"""



@app.on_event("startup")
async def startup():
    async with aiosqlite.connect("mensajes.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS mensajes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT,
                whatsapp_id TEXT,
                nombre TEXT,
                mensaje_recibido TEXT,
                mensaje_enviado TEXT
            )
        """)
        await db.commit()

import datetime

async def guardar_mensaje(fecha, whatsapp_id, nombre, mensaje_recibido, mensaje_enviado):
    async with aiosqlite.connect("mensajes.db") as db:
        await db.execute("""
            INSERT INTO mensajes (fecha, whatsapp_id, nombre, mensaje_recibido, mensaje_enviado)
            VALUES (?, ?, ?, ?, ?)
        """, (fecha, whatsapp_id, nombre, mensaje_recibido, mensaje_enviado))
        await db.commit()

from fastapi.responses import JSONResponse

# Recupera los últimos N turnos de conversación (usuario y bot) para un usuario específico
async def get_historial_usuario(whatsapp_id, n=6):
    historial = []
    async with aiosqlite.connect("mensajes.db") as db:
        async with db.execute(
            "SELECT mensaje_recibido, mensaje_enviado FROM mensajes WHERE whatsapp_id = ? ORDER BY fecha DESC LIMIT ?", (whatsapp_id, n)
        ) as cursor:
            rows = await cursor.fetchall()
            # Los mensajes se traen del más reciente al más antiguo, así que los invertimos para mantener el orden correcto
            for recibido, enviado in reversed(rows):
                if recibido:
                    historial.append({"role": "user", "content": recibido})
                if enviado:
                    historial.append({"role": "assistant", "content": enviado})
    return historial


@app.get("/mensajes_test")
async def mensajes_test():
    mensajes = []
    async with aiosqlite.connect("mensajes.db") as db:
        async with db.execute("SELECT fecha, whatsapp_id, nombre, mensaje_recibido, mensaje_enviado FROM mensajes ORDER BY fecha DESC LIMIT 20") as cursor:
            async for row in cursor:
                fecha, whatsapp_id, nombre, mensaje_recibido, mensaje_enviado = row
                mensajes.append({
                    "fecha": fecha,
                    "whatsapp_id": whatsapp_id,
                    "nombre": nombre,
                    "mensaje_recibido": mensaje_recibido,
                    "mensaje_enviado": mensaje_enviado,
                })
    return JSONResponse(content=mensajes)
    
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
        # 1. Recupera historial reciente del usuario (por ejemplo, 6 turnos)
        historial = await get_historial_usuario(sender, n=6)

        # 2. Construye el contexto de mensajes para OpenAI
        mensajes_openai = [{"role": "system", "content": system_prompt}] + historial + [{"role": "user", "content": text}]

        # 3. Llama a OpenAI con historial
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=mensajes_openai
        )
        reply = response.choices[0].message.content.strip()

        # Extraer nombre y teléfono (si existe profile)
        if "contacts" in value and value["contacts"]:
            nombre_contacto = value["contacts"][0].get("profile", {}).get("name", "Sin nombre")
            telefono_contacto = value["contacts"][0]["wa_id"]
        else:
            nombre_contacto = "Desconocido"
            telefono_contacto = sender

        # ====== GUARDAR EL MENSAJE EN LA BASE DE DATOS ======
        fecha_actual = datetime.datetime.utcnow().isoformat()
        await guardar_mensaje(
            fecha_actual,
            telefono_contacto,
            nombre_contacto,
            text,
            reply
        )
        # ====== FIN GUARDADO MENSAJE ======

        # --- Crear lead en Odoo ---
        # --- Control anti-duplicación de lead (protege contra múltiples mensajes rápidos) ---
        already_lead = False  # Inicializa la variable fuera del bloque async

        async with aiosqlite.connect("mensajes.db") as db:
            # Verifica si ya existe lead para este usuario
            async with db.execute(
                "SELECT id FROM mensajes WHERE whatsapp_id=? AND mensaje_enviado LIKE '%Lead creado en Odoo%' ORDER BY fecha DESC LIMIT 1",
                (telefono_contacto,)
            ) as cursor:
                row = await cursor.fetchone()
                already_lead = row is not None
        
        if not already_lead:
            # Crea el lead en Odoo
            crear_lead_odoo(nombre_contacto, telefono_contacto, text)
            print(f"✅ Lead enviado a Odoo: {nombre_contacto} ({telefono_contacto})")
            # Graba en la BD que ya se creó el lead
            async with aiosqlite.connect("mensajes.db") as db:
                await db.execute(
                    "INSERT INTO mensajes (whatsapp_id, mensaje_enviado, fecha) VALUES (?, ?, datetime('now'))",
                    (telefono_contacto, f"Lead creado en Odoo para {nombre_contacto}",)
                )
                await db.commit()
        else:
            print(f"ℹ️ Ya existe lead creado para {telefono_contacto}. No se crea lead nuevo.")

        
        # --- Fin del control anti-duplicación de lead ---

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
    
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    page: int = 1,
    q: str = "",
    credentials: HTTPBasicCredentials = Depends(check_auth)
):
    # Parámetros de paginación
    page_size = 50
    offset = (page - 1) * page_size

    # Buscador SQL (búsqueda básica en varios campos)
    search_sql = ""
    params = []
    if q:
        search_sql = """WHERE 
            fecha LIKE ? OR 
            whatsapp_id LIKE ? OR 
            nombre LIKE ? OR 
            mensaje_recibido LIKE ? OR 
            mensaje_enviado LIKE ?"""
        search_term = f"%{q}%"
        params.extend([search_term] * 5)

    # Total de mensajes (para paginación)
    async with aiosqlite.connect("mensajes.db") as db:
        async with db.execute(f"SELECT COUNT(*) FROM mensajes {search_sql}", params) as cursor:
            total = (await cursor.fetchone())[0]

        # Mensajes de la página
        async with db.execute(
            f"""SELECT id, fecha, whatsapp_id, nombre, mensaje_recibido, mensaje_enviado 
            FROM mensajes {search_sql} 
            ORDER BY fecha DESC LIMIT ? OFFSET ?""",
            params + [page_size, offset]
        ) as cursor:
            mensajes = await cursor.fetchall()

    # HTML
    html = f"""
    <html>
    <head>
        <title>Mensajes WhatsApp - Dashboard</title>
        <style>
            body {{ font-family: Arial, sans-serif; padding: 10px; }}
            table {{ border-collapse: collapse; width: 100%; font-size: 15px; }}
            th, td {{ border: 1px solid #dddddd; padding: 8px; word-break: break-all; }}
            th {{ background-color: #f2f2f2; }}
            tr:nth-child(even) {{ background-color: #fafafa; }}
            input[type='text']{{ font-size:15px; padding:4px; }}
            button, .btn-small {{ font-size:15px; padding:4px 10px; margin: 2px; cursor:pointer; }}
            @media (max-width: 700px) {{
                table, thead, tbody, th, td, tr {{ display:block; }}
                th, td {{ border: none; }}
                td {{ padding: 8px 0; }}
                tr {{ margin-bottom: 15px; border-bottom: 1px solid #ddd; }}
            }}
        </style>
        <script>
            function borrar(id) {{
                if(confirm('¿Seguro que quieres borrar este mensaje?')){{
                    fetch('/borrar_mensaje?id=' + id)
                        .then(r => location.reload());
                }}
            }}
            function descargarCSV() {{
                window.location = '/descargar_csv?q=' + encodeURIComponent(document.getElementById('q').value);
            }}
        </script>
    </head>
    <body>
    <h2>Mensajes WhatsApp (página {page} de {((total-1)//page_size)+1})</h2>
    <form method="get" style="margin-bottom:10px;">
        <input type="text" id="q" name="q" value="{q}" placeholder="Buscar...">
        <button type="submit">Buscar</button>
        <button type="button" onclick="descargarCSV()">Descargar CSV</button>
    </form>
    <table>
        <tr>
            <th>Fecha</th>
            <th>WhatsApp ID</th>
            <th>Nombre</th>
            <th>Recibido</th>
            <th>Enviado</th>
            <th></th>
        </tr>
    """
    for row in mensajes:
        id, fecha, whatsapp_id, nombre, mensaje_recibido, mensaje_enviado = row
        html += f"""<tr>
        <td>{fecha}</td>
        <td>{whatsapp_id}</td>
        <td>{nombre}</td>
        <td>{mensaje_recibido}</td>
        <td>{mensaje_enviado}</td>
        <td><button class='btn-small' onclick="borrar({id})">🗑️</button></td>
        </tr>"""

    html += "</table><div style='margin-top:12px;'>"

    if page > 1:
        html += f'<a href="?page={page-1}&q={q}"><button>&larr; Anterior</button></a>'
    if offset + page_size < total:
        html += f'<a href="?page={page+1}&q={q}"><button>Siguiente &rarr;</button></a>'

    html += "</div></body></html>"
    return HTMLResponse(content=html)

@app.get("/borrar_mensaje")
async def borrar_mensaje(id: int, credentials: HTTPBasicCredentials = Depends(check_auth)):
    async with aiosqlite.connect("mensajes.db") as db:
        await db.execute("DELETE FROM mensajes WHERE id = ?", (id,))
        await db.commit()
    return {"status": "ok"}

@app.get("/descargar_csv")
async def descargar_csv(q: str = "", credentials: HTTPBasicCredentials = Depends(check_auth)):
    search_sql = ""
    params = []
    if q:
        search_sql = """WHERE 
            fecha LIKE ? OR 
            whatsapp_id LIKE ? OR 
            nombre LIKE ? OR 
            mensaje_recibido LIKE ? OR 
            mensaje_enviado LIKE ?"""
        search_term = f"%{q}%"
        params.extend([search_term] * 5)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Fecha", "WhatsApp ID", "Nombre", "Recibido", "Enviado"])

    async with aiosqlite.connect("mensajes.db") as db:
        async with db.execute(
            f"""SELECT fecha, whatsapp_id, nombre, mensaje_recibido, mensaje_enviado 
            FROM mensajes {search_sql} 
            ORDER BY fecha DESC""",
            params
        ) as cursor:
            async for row in cursor:
                writer.writerow(row)

    output.seek(0)
    return StreamingResponse(iter([output.read()]), media_type="text/csv", headers={
        "Content-Disposition": "attachment; filename=mensajes.csv"
    })
