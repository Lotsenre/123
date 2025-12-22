import uuid
from datetime import datetime
from typing import List, Optional, Tuple
from app.repositories.ticket_repository import TrainRepository, WagonRepository, SeatRepository, TicketRepository
from app.models.tickets import Train, Wagon, Seat, Ticket, DiscountType
from app.schemes.ticket_schemes import (
    TrainCreate, WagonCreate, PriceCalculationRequest, PriceCalculationResponse, TicketCreate
)

class DiscountService:
    """Сервис для расчета скидок"""
    
    DISCOUNT_RATES = {
        "child": 0.50,      # 50% скидка для детей (0-12 лет)
        "student": 0.25,    # 25% скидка для студентов
        "pensioner": 0.40,  # 40% скидка для пенсионеров
        "none": 0.0         # Нет скидки
    }
    
    @staticmethod
    def get_discount_percent(discount_type: str) -> float:
        """Получить процент скидки по типу"""
        return DiscountService.DISCOUNT_RATES.get(discount_type, 0.0)
    
    @staticmethod
    def calculate_final_price(base_price: float, discount_type: str) -> Tuple[float, float]:
        """Рассчитать финальную цену с учетом скидки"""
        discount_percent = DiscountService.get_discount_percent(discount_type)
        discount_amount = base_price * discount_percent
        final_price = base_price - discount_amount
        return final_price, discount_percent * 100

class TrainService:
    """Сервис для управления поездами"""
    
    def __init__(self, train_repo: TrainRepository):
        self.train_repo = train_repo
    
    async def create_train(self, train_data: TrainCreate) -> Train:
        """Создать новый поезд"""
        train = Train(**train_data.model_dump())
        return await self.train_repo.create_train(train)
    
    async def search_trains(self, route_from: str, route_to: str) -> List[Train]:
        """Поиск поездов по маршруту"""
        return await self.train_repo.search_trains(route_from, route_to)
    
    async def get_train(self, train_id: int) -> Optional[Train]:
        """Получить информацию о поезде"""
        return await self.train_repo.get_train(train_id)
    
    async def get_all_trains(self) -> List[Train]:
        """Получить все активные поезда"""
        return await self.train_repo.get_all_trains()

class WagonService:
    """Сервис для управления вагонами"""
    
    WAGON_TYPE_MULTIPLIERS = {
        "platzkart": 1.0,   # Плацкарт - базовая цена
        "coupe": 1.5,       # Купе - 1.5x цена
        "suite": 2.0        # Люкс - 2x цена
    }
    
    def __init__(self, wagon_repo: WagonRepository, seat_repo: SeatRepository):
        self.wagon_repo = wagon_repo
        self.seat_repo = seat_repo
    
    async def create_wagon(self, wagon_data: WagonCreate) -> Wagon:
        """Создать новый вагон"""
        wagon = Wagon(**wagon_data.model_dump())
        return await self.wagon_repo.create_wagon(wagon)
    
    async def get_wagon(self, wagon_id: int) -> Optional[Wagon]:
        """Получить информацию о вагоне"""
        return await self.wagon_repo.get_wagon(wagon_id)
    
    async def get_wagons_by_train(self, train_id: int) -> List[Wagon]:
        """Получить все вагоны поезда"""
        return await self.wagon_repo.get_wagons_by_train(train_id)
    
    async def get_wagons_by_type(self, train_id: int, wagon_type: str) -> List[Wagon]:
        """Получить вагоны определенного типа в поезде"""
        return await self.wagon_repo.get_wagons_by_type(train_id, wagon_type)
    
    def get_price_multiplier(self, wagon_type: str) -> float:
        """Получить множитель цены для типа вагона"""
        return self.WAGON_TYPE_MULTIPLIERS.get(wagon_type, 1.0)

class SeatService:
    """Сервис для управления местами"""
    
    def __init__(self, seat_repo: SeatRepository):
        self.seat_repo = seat_repo
    
    async def create_seats(self, wagon_id: int, total_seats: int) -> List[Seat]:
        """Создать места для вагона"""
        seats = []
        for seat_number in range(1, total_seats + 1):
            seat = Seat(wagon_id=wagon_id, seat_number=seat_number)
            seats.append(seat)
        
        for seat in seats:
            await self.seat_repo.create_seat(seat)
        
        return seats
    
    async def get_seat(self, seat_id: int) -> Optional[Seat]:
        """Получить информацию о месте"""
        return await self.seat_repo.get_seat(seat_id)
    
    async def get_available_seats(self, wagon_id: int) -> List[Seat]:
        """Получить свободные места в вагоне"""
        return await self.seat_repo.get_available_seats(wagon_id)
    
    async def get_wagon_layout(self, wagon_id: int) -> List[Seat]:
        """Получить всю схему мест вагона"""
        return await self.seat_repo.get_all_seats(wagon_id)
    
    async def reserve_seat(self, seat_id: int) -> Seat:
        """Зарезервировать место"""
        return await self.seat_repo.reserve_seat(seat_id)
    
    async def release_seat(self, seat_id: int) -> Seat:
        """Освободить место (отменить резервацию)"""
        return await self.seat_repo.release_seat(seat_id)
    
    async def count_available_seats(self, wagon_id: int) -> int:
        """Подсчитать количество свободных мест"""
        available = await self.get_available_seats(wagon_id)
        return len(available)

class TicketService:
    """Сервис для управления билетами"""
    
    def __init__(self, ticket_repo: TicketRepository, seat_repo: SeatRepository):
        self.ticket_repo = ticket_repo
        self.seat_repo = seat_repo
    
    def _generate_ticket_number(self) -> str:
        """Сгенерировать номер билета"""
        return f"WM-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
    
    async def calculate_price(self, 
                            train: Train, 
                            wagon: Wagon, 
                            discount_type: str = "none") -> PriceCalculationResponse:
        """Рассчитать стоимость билета"""
        base_price = train.base_price * wagon.price_multiplier
        final_price, discount_percent = DiscountService.calculate_final_price(base_price, discount_type)
        
        return PriceCalculationResponse(
            base_price=base_price,
            discount_percent=discount_percent,
            final_price=final_price,
            discount_type=discount_type
        )
    
    async def create_ticket(self, 
                          ticket_data: TicketCreate,
                          base_price: float,
                          final_price: float,
                          train: Train) -> Ticket:
        """Создать билет и зарезервировать место"""
        # Рассчитать скидку
        _, discount_percent = DiscountService.calculate_final_price(base_price, ticket_data.discount_type)
        
        # Создать билет
        ticket = Ticket(
            train_id=ticket_data.train_id,
            wagon_id=ticket_data.wagon_id,
            seat_id=ticket_data.seat_id,
            passenger_name=ticket_data.passenger_name,
            passenger_email=ticket_data.passenger_email,
            passenger_phone=ticket_data.passenger_phone,
            discount_type=ticket_data.discount_type,
            discount_percent=discount_percent,
            base_price=base_price,
            final_price=final_price,
            ticket_number=self._generate_ticket_number(),
            departure_time=train.departure_time,
            arrival_time=train.arrival_time,
            is_paid=False
        )
        
        # Зарезервировать место
        await self.seat_repo.reserve_seat(ticket_data.seat_id)
        
        # Сохранить билет
        return await self.ticket_repo.create_ticket(ticket)
    
    async def get_ticket(self, ticket_id: int) -> Optional[Ticket]:
        """Получить информацию о билете"""
        return await self.ticket_repo.get_ticket(ticket_id)
    
    async def get_user_tickets(self, passenger_email: str) -> List[Ticket]:
        """Получить все билеты пассажира"""
        return await self.ticket_repo.get_user_tickets(passenger_email)
    
    async def delete_ticket(self, ticket_id: int) -> bool:
        """Удалить билет"""
        return await self.ticket_repo.delete_ticket(ticket_id)
    
    async def pay_ticket(self, ticket_id: int) -> Ticket:
        """Оплатить билет"""
        return await self.ticket_repo.update_ticket_payment(ticket_id, True)
    
    async def generate_pdf_ticket(self, ticket: Ticket, train: Train, wagon: Wagon, seat: Seat) -> dict:
        """Сгенерировать данные для электронного билета"""
        return {
            "ticket_number": ticket.ticket_number,
            "passenger_name": ticket.passenger_name,
            "train_number": train.train_number,
            "wagon_number": wagon.wagon_number,
            "wagon_type": wagon.wagon_type,
            "seat_number": seat.seat_number,
            "route_from": train.route_from,
            "route_to": train.route_to,
            "departure_time": train.departure_time,
            "arrival_time": train.arrival_time,
            "discount_type": ticket.discount_type,
            "base_price": ticket.base_price,
            "discount_percent": ticket.discount_percent,
            "final_price": ticket.final_price,
            "is_paid": ticket.is_paid,
            "issued_date": ticket.created_at
        }