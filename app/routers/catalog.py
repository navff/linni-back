from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/api/catalog", tags=["catalog"])

CARS_JSON_URL = "https://raw.githubusercontent.com/blanzh/carsBase/master/cars.json"

# Кэш: список марок, загружается один раз при старте приложения.
# Каждый элемент: {"id": str, "name": str, "cyrillic_name": str, "models": [...]}
_catalog: list[dict] = []


async def load_catalog() -> None:
    """Загружает справочник с GitHub. Вызывается из lifespan."""
    import httpx

    global _catalog
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(CARS_JSON_URL)
        response.raise_for_status()
        _catalog = response.json()


# ---------- Схемы ответов ----------

class MakeResponse(BaseModel):
    id: str
    name: str
    cyrillic_name: str
    country: str | None = None


class ModelResponse(BaseModel):
    id: str
    name: str
    cyrillic_name: str
    year_from: int | None = None
    year_to: int | None = None


# ---------- Эндпоинты ----------

@router.get("/makes", response_model=list[MakeResponse], summary="Поиск марки по подстроке (≥2 символа)")
async def search_makes(
    q: str = Query(..., min_length=2, description="Строка поиска (латиница или кириллица)"),
):
    if not _catalog:
        raise HTTPException(status_code=503, detail="Справочник ещё не загружен, попробуйте позже")

    q_lower = q.lower()
    results = []
    for make in _catalog:
        if q_lower in make.get("name", "").lower() or q_lower in make.get("cyrillic_name", "").lower():
            results.append(
                MakeResponse(
                    id=make["id"],
                    name=make["name"],
                    cyrillic_name=make.get("cyrillic_name", ""),
                    country=make.get("country"),
                )
            )
    return results


@router.get("/makes/{make_id}/models", response_model=list[ModelResponse], summary="Список моделей по марке")
async def get_models(make_id: str):
    if not _catalog:
        raise HTTPException(status_code=503, detail="Справочник ещё не загружен, попробуйте позже")

    for make in _catalog:
        if make["id"].lower() == make_id.lower():
            return [
                ModelResponse(
                    id=m["id"],
                    name=m["name"],
                    cyrillic_name=m.get("cyrillic_name", ""),
                    year_from=m.get("year_from"),
                    year_to=m.get("year_to"),
                )
                for m in make.get("models", [])
            ]

    raise HTTPException(status_code=404, detail=f"Марка '{make_id}' не найдена")
