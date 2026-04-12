import uuid
from datetime import date, datetime

from pydantic import BaseModel, field_validator


class ServiceRecordCreate(BaseModel):
    title: str
    date: date
    mileage: int
    cost: float | None = None
    workshop: str | None = None
    notes: str | None = None

    @field_validator("mileage")
    @classmethod
    def mileage_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Пробег должен быть больше 0")
        return v

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Наименование не может быть пустым")
        return v.strip()


class ServiceRecordUpdate(ServiceRecordCreate):
    pass


class ServiceRecordResponse(BaseModel):
    id: uuid.UUID
    carId: uuid.UUID
    title: str
    date: date
    mileage: int
    cost: float | None
    workshop: str | None
    notes: str | None
    attachments: list[str]
    createdAt: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_model(cls, record) -> "ServiceRecordResponse":
        return cls(
            id=record.id,
            carId=record.car_id,
            title=record.title,
            date=record.date,
            mileage=record.mileage,
            cost=float(record.cost) if record.cost is not None else None,
            workshop=record.workshop,
            notes=record.notes,
            attachments=[a.url for a in record.attachments],
            createdAt=record.created_at,
        )


class ShareTokenResponse(BaseModel):
    token: str
    shareUrl: str
