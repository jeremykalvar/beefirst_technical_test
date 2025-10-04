import logging
import sys

from fastapi import FastAPI, Request, Response, status
from pydantic import BaseModel, EmailStr

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)sZ %(levelname)s %(message)s")

app = FastAPI(title="SMTP Mock", version="1.0.0")

class SendEmail(BaseModel):
    to: EmailStr
    subject: str
    body: str

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}

@app.post("/send", status_code=status.HTTP_202_ACCEPTED)
async def send(payload: SendEmail, request: Request) -> Response:
    idem = request.headers.get("Idempotency-Key")
    logging.info("SMTP-MOCK send to=%s subject=%r idem=%s body=%r", payload.to, payload.subject, idem, payload.body)
    return Response(status_code=status.HTTP_202_ACCEPTED)
