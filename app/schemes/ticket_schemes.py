from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
from typing import Optional, List
from enum import Enum


class DiscountTypeEnum(str, Enum):
    """Допустимые типы скидок"""
    CHILD = "child"
    STUDENT = "student"
    PENSIONER = "pensioner"
    NONE = "none"


class WagonTypeEnum(str, Enum):
    """Допустимые типы вагонов"""
    PLATZKART = "platzkart"
    COUPE = "coupe"
    SUITE = "suite"


class TrainBase(BaseModel):
    train_number: str = Field(min_length=1, max_length=50)
    route_from: str = Field(min_length=1, max_length=100)
    route_to: str = Field(min_length=1, max_length=100)
    departure_time: datetime
    arrival_time: datetime
    duration_hours: int = Field(gt=0)
    base_price: float = Field(gt=0)

    @field_validator('arrival_time')
    @classmethod
    def arrival_after_departure(cls, v, info):
        if 'departure_time' in info.data and v <= info.data['departure_time']:
            raise ValueError('Время прибытия должно быть позже времени отправления')
        return v

class TrainCreate(TrainBase):
    is_active: bool = True

class TrainResponse(TrainBase):
    id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class WagonBase(BaseModel):
    wagon_number: int = Field(gt=0)
    wagon_type: WagonTypeEnum
    total_seats: int = Field(gt=0)
    price_multiplier: float = Field(default=1.0, gt=0)

class WagonCreate(WagonBase):
    train_id: int

class WagonResponse(WagonBase):
    id: int
    train_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class SeatBase(BaseModel):
    seat_number: int
    is_available: bool = True
    is_reserved: bool = False

class SeatResponse(SeatBase):
    id: int
    wagon_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class WagonWithSeatsResponse(WagonResponse):
    seats: List[SeatResponse] = []

class DiscountRequest(BaseModel):
    discount_type: DiscountTypeEnum

class PriceCalculationRequest(BaseModel):
    train_id: int
    wagon_id: int
    seat_id: int
    discount_type: DiscountTypeEnum = DiscountTypeEnum.NONE

class PriceCalculationResponse(BaseModel):
    base_price: float
    discount_percent: float
    final_price: float
    discount_type: str

class TicketBase(BaseModel):
    train_id: int
    wagon_id: int
    seat_id: int
    passenger_name: str = Field(min_length=1, max_length=200)
    passenger_email: EmailStr
    passenger_phone: str = Field(default="", max_length=20)
    discount_type: DiscountTypeEnum = DiscountTypeEnum.NONE

class TicketCreate(TicketBase):
    pass

class TicketResponse(TicketBase):
    id: int
    ticket_number: str
    base_price: float
    final_price: float
    discount_percent: float
    is_paid: bool
    created_at: datetime
    departure_time: datetime
    arrival_time: datetime
    
    class Config:
        from_attributes = True

class TicketDetailResponse(TicketResponse):
    train_number: str
    wagon_number: int
    wagon_type: str
    seat_number: int
    route_from: str
    route_to: str

class SearchRequest(BaseModel):
    route_from: str
    route_to: str
    departure_date: datetime

class TrainScheduleResponse(BaseModel):
    id: int
    train_number: str
    route_from: str
    route_to: str
    departure_time: datetime
    arrival_time: datetime
    duration_hours: int
    base_price: float
    available_seats_count: int = 0
    wagons: List[WagonResponse] = []

class PaymentRequest(BaseModel):
    ticket_id: int
    amount: float

class PaymentResponse(BaseModel):
    ticket_id: int
    is_paid: bool
    payment_date: datetime
