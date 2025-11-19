from fastapi import FastAPI, Request

app = FastAPI()

@app.get("/")
async def root():
    return {"status": "online"}

@app.post("/gohighlevel/webhook")
async def ghl_webhook(request: Request):
    body = await request.json()
    print("🔔 Incoming GHL Webhook:", body)
    
    # Temporary response — we will replace this later
    return {"received": True, "message": "Webhook OK"}