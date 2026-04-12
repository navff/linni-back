from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import cars, records, share
from .routers import catalog
from .routers.catalog import load_catalog


@asynccontextmanager
async def lifespan(app: FastAPI):
    await load_catalog()
    yield


app = FastAPI(title="Линни API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cars.router)
app.include_router(records.router)
app.include_router(share.router)
app.include_router(catalog.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
