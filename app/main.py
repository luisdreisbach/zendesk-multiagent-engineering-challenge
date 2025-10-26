from dotenv import load_dotenv
from fastapi import FastAPI

from app.api.routers import create_router
from app.logger import setup_logger
from app.telemetry.otel import add_instrumentation

setup_logger()
load_dotenv()

app = FastAPI(title="Zendesk E-commerce Assistant")
app.include_router(create_router())

add_instrumentation(app)


@app.get("/health", tags=["system"])
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
