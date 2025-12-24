from typing import TYPE_CHECKING
from sqlalchemy import String, Float, DateTime, Boolean, Enum, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.database import Base
from datetime import datetime
import enum

if TYPE_CHECKING:
    pass

class TrainType(str, enum.Enum):
    PLATZKART = "platzkart"  # Плацкарт
    COUPE = "coupe"  # Купе
    SUITE = "suite"  # Люкс

class DiscountType(str, enum.Enum):
    CHILD = "child"  # Детский
    STUDENT = "student"  # Студенческий
    PENSIONER = "pensioner"  # Пенсионер
    NONE = "none"  # Без скидки

class Train(Base):
    __tablename__ = "trains"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    train_number: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    route_from: Mapped[str] = mapped_column(String(100), index=True)
    route_to: Mapped[str] = mapped_column(String(100), index=True)
    departure_time: Mapped[datetime] = mapped_column(DateTime)
    arrival_time: Mapped[datetime] = mapped_column(DateTime)
    duration_hours: Mapped[int] = mapped_column(Integer)
    base_price: Mapped[float] = mapped_column(Float)  # Базовая цена за место
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships для SQLAdmin
    wagons: Mapped[list["Wagon"]] = relationship(back_populates="train", cascade="all, delete-orphan")
    tickets: Mapped[list["Ticket"]] = relationship(back_populates="train", cascade="all, delete-orphan")

class Wagon(Base):
    __tablename__ = "wagons"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    train_id: Mapped[int] = mapped_column(ForeignKey("trains.id"), index=True)
    wagon_number: Mapped[int] = mapped_column(Integer)
    wagon_type: Mapped[str] = mapped_column(String(20))  # platzkart, coupe, suite
    total_seats: Mapped[int] = mapped_column(Integer)
    price_multiplier: Mapped[float] = mapped_column(Float, default=1.0)  # Множитель цены в зависимости от типа

    # Relationships для SQLAdmin
    train: Mapped["Train"] = relationship(back_populates="wagons")
    seats: Mapped[list["Seat"]] = relationship(back_populates="wagon", cascade="all, delete-orphan")
    tickets: Mapped[list["Ticket"]] = relationship(back_populates="wagon", cascade="all, delete-orphan")

class Seat(Base):
    __tablename__ = "seats"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    wagon_id: Mapped[int] = mapped_column(ForeignKey("wagons.id"), index=True)
    seat_number: Mapped[int] = mapped_column(Integer)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    is_reserved: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships для SQLAdmin
    wagon: Mapped["Wagon"] = relationship(back_populates="seats")
    tickets: Mapped[list["Ticket"]] = relationship(back_populates="seat", cascade="all, delete-orphan")

class Ticket(Base):
    __tablename__ = "tickets"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    train_id: Mapped[int] = mapped_column(ForeignKey("trains.id"), index=True)
    wagon_id: Mapped[int] = mapped_column(ForeignKey("wagons.id"), index=True)
    seat_id: Mapped[int] = mapped_column(ForeignKey("seats.id"), index=True)
    passenger_name: Mapped[str] = mapped_column(String(200))
    passenger_email: Mapped[str] = mapped_column(String(200))
    passenger_phone: Mapped[str] = mapped_column(String(20))
    discount_type: Mapped[str] = mapped_column(String(20), default="none")
    discount_percent: Mapped[float] = mapped_column(Float, default=0.0)
    base_price: Mapped[float] = mapped_column(Float)
    final_price: Mapped[float] = mapped_column(Float)
    ticket_number: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    is_paid: Mapped[bool] = mapped_column(Boolean, default=False)
    departure_time: Mapped[datetime] = mapped_column(DateTime)
    arrival_time: Mapped[datetime] = mapped_column(DateTime)

    # Relationships для SQLAdmin - ВАЖНО для админ панели!
    train: Mapped["Train"] = relationship(back_populates="tickets")
    wagon: Mapped["Wagon"] = relationship(back_populates="tickets")
    seat: Mapped["Seat"] = relationship(back_populates="tickets")
