from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

from .config import settings
from .database import engine, warmup_db
from .routers import cars, records, share, maintenance, suggestions
from .routers import catalog
from .routers.catalog import load_catalog
from .telemetry import setup_telemetry


@asynccontextmanager
async def lifespan(app: FastAPI):
    await load_catalog()
    await warmup_db()
    yield


setup_telemetry(settings.MONIUM_API_KEY, settings.MONIUM_PROJECT)

app = FastAPI(title="Линни API", version="1.0.0", lifespan=lifespan)

FastAPIInstrumentor.instrument_app(app)
SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cars.router)
app.include_router(records.router)
app.include_router(maintenance.router)
app.include_router(share.router)
app.include_router(catalog.router)
app.include_router(suggestions.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
