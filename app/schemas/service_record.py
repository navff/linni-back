import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator
from pydantic.alias_generators import to_camel


class ServiceRecordCreate(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    record_type: Literal["service", "fuel"] = "service"
    title: str = ""
    date: date
    mileage: int | None = None
    cost: float | None = None
    workshop: str | None = None
    notes: str | None = None
    fuel_liters: float | None = None

    @model_validator(mode="after")
    def validate_by_type(self) -> "ServiceRecordCreate":
        if self.record_type == "service":
            if not self.title.strip():
                raise ValueError("Наименование не может быть пустым")
            self.title = self.title.strip()
            if self.mileage is None or self.mileage <= 0:
                raise ValueError("Укажите пробег")
        else:
            if self.fuel_liters is None or self.fuel_liters <= 0:
                raise ValueError("Укажите количество литров")
            if not self.title.strip():
                self.title = "Заправка"
            if self.mileage is not None and self.mileage <= 0:
                raise ValueError("Пробег должен быть больше 0")
        return self


class ServiceRecordUpdate(ServiceRecordCreate):
    pass


class ServiceRecordResponse(BaseModel):
    id: uuid.UUID
    carId: uuid.UUID
    recordType: str
    title: str
    date: date
    mileage: int | None
    cost: float | None
    workshop: str | None
    notes: str | None
    fuelLiters: float | None
    consumptionPer100km: float | None
    attachments: list[str]
    createdAt: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_model(cls, record) -> "ServiceRecordResponse":
        return cls(
            id=record.id,
            carId=record.car_id,
            recordType=record.record_type,
            title=record.title,
            date=record.date,
            mileage=record.mileage,
            cost=float(record.cost) if record.cost is not None else None,
            workshop=record.workshop,
            notes=record.notes,
            fuelLiters=float(record.fuel_liters) if record.fuel_liters is not None else None,
            consumptionPer100km=float(record.consumption_per_100km) if record.consumption_per_100km is not None else None,
            attachments=[a.url for a in record.attachments],
            createdAt=record.created_at,
        )


class ShareTokenResponse(BaseModel):
    token: str
    shareUrl: str
