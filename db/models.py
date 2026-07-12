from datetime import datetime, date, time

from sqlalchemy import (
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    Boolean,
    Integer,
    Date,
    Time,
    DateTime,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Trainer(Base):
    __tablename__ = "trainer"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    must_set_password: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    remember_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    erstellte_termine: Mapped[list["Termin"]] = relationship(
        back_populates="ersteller", cascade="all, delete-orphan"
    )
    anmeldungen: Mapped[list["Anmeldung"]] = relationship(
        back_populates="trainer", cascade="all, delete-orphan"
    )


class Termin(Base):
    __tablename__ = "termin"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    location: Mapped[str] = mapped_column(String(200), nullable=False)
    needed_trainers: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    email_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    cancelled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by_trainer_id: Mapped[int] = mapped_column(ForeignKey("trainer.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    ersteller: Mapped["Trainer"] = relationship(back_populates="erstellte_termine")
    anmeldungen: Mapped[list["Anmeldung"]] = relationship(
        back_populates="termin", cascade="all, delete-orphan"
    )
    teilnahmen: Mapped[list["Teilnahme"]] = relationship(
        back_populates="termin", cascade="all, delete-orphan"
    )


class Anmeldung(Base):
    __tablename__ = "anmeldung"
    __table_args__ = (UniqueConstraint("termin_id", "trainer_id", name="uq_termin_trainer"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    termin_id: Mapped[int] = mapped_column(ForeignKey("termin.id"), nullable=False)
    trainer_id: Mapped[int] = mapped_column(ForeignKey("trainer.id"), nullable=False)
    registered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    termin: Mapped["Termin"] = relationship(back_populates="anmeldungen")
    trainer: Mapped["Trainer"] = relationship(back_populates="anmeldungen")


class Teilnahme(Base):
    __tablename__ = "teilnahme"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    termin_id: Mapped[int] = mapped_column(ForeignKey("termin.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    registered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    termin: Mapped["Termin"] = relationship(back_populates="teilnahmen")
