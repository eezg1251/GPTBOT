import os
import openai
import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

# Cargar variables de entorno desde secrets
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
META_TOKEN = os.environ.get("META_TOKEN")
META_PHONE_NUMBER_ID = os.environ.get("META_PHONE_NUMBER_ID")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")

# Configurar clave de OpenAI
openai.api_key = OPENAI_API_KEY

@app.get("/")
def root():
    return {"message": "Servidor de WhatsApp IA activo 🚀"}

# Verificación de webhook (GET)
@app.get("/webhook")
def verify_webhook(request: Request):
    params = dict(request.query_params)
    if (
        params.get("hub.mode") == "subscribe"
        and params.get("hub.verify_token") == VERIFY_TOKEN
    ):
        return int(params.get("hub.challenge"))
    return JSONResponse(status_code=403, content={"error": "Token inválido"})

# Recepción de mensajes de WhatsApp (POST)
@app.post("/webhook")
async def receive_message(request: Request):
    data = await request.json()
    try:
        entry = data["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]
        messages = value.get("messages")

        if messages:
            message = messages[0]
            user_text = message["text"]["body"]
            sender_id = message["from"]

            # Obtener respuesta IA
            response_text = ask_openai(user_text)

            # Enviar respuesta por WhatsApp
            send_whatsapp_message(sender_id, response_text)

        return {"status": "ok"}

    except Exception as e:
        print("❌ Error en /webhook:", e)
        return JSONResponse(status_code=500, content={"error": str(e)})

# Función: llamar a OpenAI GPT-3.5
def ask_openai(user_input: str) -> str:
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Más barato
            messages=[
                {"role": "system", "content": "Eres un asistente útil y claro que responde en español a preguntas de clientes de una consultora."},
                {"role": "user", "content": user_input}
            ],
            max_tokens=250,
            temperature=0.6,
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        print("❌ Error con OpenAI:", e)
        return "Lo siento, ocurrió un error al procesar tu mensaje."

# Función: responder al cliente por WhatsApp
def send_whatsapp_message(recipient_id: str, text: str):
    url = f"https://graph.facebook.com/v18.0/{META_PHONE_NUMBER_ID}/messages"
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

    try:
        res = requests.post(url, json=payload, headers=headers)
        print("✅ WhatsApp enviado:", res.status_code, res.text)
    except Exception as e:
        print("❌ Error enviando WhatsApp:", e)
