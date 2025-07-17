import os
import openai
import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

# Tokens desde secrets
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")
META_TOKEN = os.environ.get("META_TOKEN")
META_PHONE_NUMBER_ID = os.environ.get("META_PHONE_NUMBER_ID")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Configurar OpenAI
openai.api_key = OPENAI_API_KEY

@app.get("/")
def root():
    return {"message": "GPTBOT is running 🚀"}

# Verificación del webhook (GET)
@app.get("/webhook")
def verify_webhook(request: Request):
    params = dict(request.query_params)
    if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == VERIFY_TOKEN:
        return int(params.get("hub.challenge"))
    return JSONResponse(status_code=403, content={"error": "Verification failed"})

# Recepción de mensajes (POST)
@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()

    try:
        entry = data["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]
        messages = value.get("messages")

        if messages:
            message = messages[0]
            user_message = message["text"]["body"]
            sender_id = message["from"]

            # Consulta a OpenAI
            ai_reply = ask_openai(user_message)

            # Enviar respuesta por WhatsApp
            send_whatsapp_message(sender_id, ai_reply)

        return {"status": "ok"}

    except Exception as e:
        print("Error:", e)
        return JSONResponse(status_code=500, content={"error": str(e)})

# Función: consulta a OpenAI GPT
def ask_openai(prompt: str) -> str:
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un asistente útil para clientes de una consultora."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=300
        )
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        return "Lo siento, hubo un error al procesar tu solicitud."

# Función: enviar mensaje por WhatsApp API
def send_whatsapp_message(recipient_id: str, message: str):
    url = f"https://graph.facebook.com/v18.0/{META_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {META_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient_id,
        "type": "text",
        "text": {"body": message}
    }
    response = requests.post(url, json=payload, headers=headers)
    print("WhatsApp API response:", response.status_code, response.text)
