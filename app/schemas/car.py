import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator
from pydantic.alias_generators import to_camel


ENGINE_TYPES = {'petrol', 'diesel', 'hybrid', 'electric'}


class CarCreate(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}

    make: str
    model: str
    year: int
    engine_type: str | None = None
    vin: str | None = None
    mileage: int
    nickname: str | None = None

    @field_validator("engine_type")
    @classmethod
    def engine_type_valid(cls, v: str | None) -> str | None:
        if v is not None and v not in ENGINE_TYPES:
            raise ValueError(f"Тип двигателя должен быть одним из: {', '.join(ENGINE_TYPES)}")
        return v

    @field_validator("mileage")
    @classmethod
    def mileage_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Пробег должен быть больше 0")
        return v

    @field_validator("year")
    @classmethod
    def year_valid(cls, v: int) -> int:
        from datetime import date
        current_year = date.today().year
        if v < 1990 or v > current_year:
            raise ValueError(f"Год должен быть от 1990 до {current_year}")
        return v

    @field_validator("vin")
    @classmethod
    def vin_valid(cls, v: str | None) -> str | None:
        if v is not None and len(v.strip()) > 0 and len(v.strip()) > 30:
            raise ValueError("VIN не может быть длиннее 30 символов")
        return v.strip() if v else None


class CarUpdate(CarCreate):
    pass


class CarMileageUpdate(BaseModel):
    mileage: int

    @field_validator("mileage")
    @classmethod
    def mileage_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Пробег должен быть больше 0")
        return v


class CarResponse(BaseModel):
    id: uuid.UUID
    userId: int
    make: str
    model: str
    year: int
    engineType: str | None
    vin: str | None
    mileage: int
    nickname: str | None
    photoUrl: str | None
    createdAt: datetime
    updatedAt: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_model(cls, car) -> "CarResponse":
        return cls(
            id=car.id,
            userId=car.user_id,
            make=car.make,
            model=car.model,
            year=car.year,
            engineType=car.engine_type,
            vin=car.vin,
            mileage=car.mileage,
            nickname=car.nickname,
            photoUrl=car.photo_url,
            createdAt=car.created_at,
            updatedAt=car.updated_at,
        )
