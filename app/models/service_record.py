import uuid
from datetime import date, datetime

from sqlalchemy import Date, ForeignKey, Integer, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class ServiceRecord(Base):
    __tablename__ = "service_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    car_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cars.id", ondelete="CASCADE"), nullable=False)
    record_type: Mapped[str] = mapped_column(Text, nullable=False, default="service")
    title: Mapped[str] = mapped_column(Text, nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    mileage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost: Mapped[float | None] = mapped_column(Numeric(10, 2))
    workshop: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    fuel_liters: Mapped[float | None] = mapped_column(Numeric(6, 2))
    consumption_per_100km: Mapped[float | None] = mapped_column(Numeric(5, 2))
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    car: Mapped["Car"] = relationship("Car", back_populates="service_records")
    attachments: Mapped[list["Attachment"]] = relationship(
        "Attachment", back_populates="record", cascade="all, delete-orphan"
    )


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("service_records.id", ondelete="CASCADE"), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)

    record: Mapped["ServiceRecord"] = relationship("ServiceRecord", back_populates="attachments")
