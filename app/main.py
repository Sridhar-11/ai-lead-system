from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse

app = FastAPI()

VERIFY_TOKEN = "my_secret_token_123"

@app.get("/")
async def home():
    return {"status": "running"}

@app.get("/webhook/meta")
async def verify_webhook(request: Request):

    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return PlainTextResponse(challenge)

    return {"error": "verification failed"}


@app.post("/webhook/meta")
async def receive_webhook(request: Request):

    data = await request.json()

    print("META WEBHOOK RECEIVED")
    print(data)

    return {"status": "ok"}