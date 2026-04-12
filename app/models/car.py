import uuid
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Integer, SmallInteger, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class Car(Base):
    __tablename__ = "cars"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    make: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    vin: Mapped[str | None] = mapped_column(Text)
    mileage: Mapped[int] = mapped_column(Integer, nullable=False)
    nickname: Mapped[str | None] = mapped_column(Text)
    photo_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="cars")
    service_records: Mapped[list["ServiceRecord"]] = relationship(
        "ServiceRecord", back_populates="car", cascade="all, delete-orphan"
    )
    share_tokens: Mapped[list["ShareToken"]] = relationship(
        "ShareToken", back_populates="car", cascade="all, delete-orphan"
    )
    maintenance_plans: Mapped[list["MaintenancePlan"]] = relationship(
        "MaintenancePlan", back_populates="car", cascade="all, delete-orphan"
    )
