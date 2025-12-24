from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, delete
from datetime import datetime, date
from typing import List, Optional
from app.models.tickets import Train, Wagon, Seat, Ticket

class TrainRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_train(self, train: Train) -> Train:
        self.session.add(train)
        await self.session.commit()
        await self.session.refresh(train)
        return train
    
    async def get_train(self, train_id: int) -> Optional[Train]:
        result = await self.session.execute(select(Train).where(Train.id == train_id))
        return result.scalar_one_or_none()
    
    async def get_train_by_number(self, train_number: str) -> Optional[Train]:
        result = await self.session.execute(select(Train).where(Train.train_number == train_number))
        return result.scalar_one_or_none()
    
    async def search_trains(self, route_from: str, route_to: str) -> List[Train]:
        result = await self.session.execute(
            select(Train).where(
                and_(
                    Train.route_from == route_from,
                    Train.route_to == route_to
                )
            )
        )
        return result.scalars().all()
    
    async def get_all_trains(self) -> List[Train]:
        result = await self.session.execute(select(Train))
        return result.scalars().all()

class WagonRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_wagon(self, wagon: Wagon) -> Wagon:
        self.session.add(wagon)
        await self.session.commit()
        await self.session.refresh(wagon)
        return wagon
    
    async def get_wagon(self, wagon_id: int) -> Optional[Wagon]:
        result = await self.session.execute(select(Wagon).where(Wagon.id == wagon_id))
        return result.scalar_one_or_none()
    
    async def get_wagons_by_train(self, train_id: int) -> List[Wagon]:
        result = await self.session.execute(select(Wagon).where(Wagon.train_id == train_id))
        return result.scalars().all()
    
    async def get_wagons_by_type(self, train_id: int, wagon_type: str) -> List[Wagon]:
        result = await self.session.execute(
            select(Wagon).where(
                and_(
                    Wagon.train_id == train_id,
                    Wagon.wagon_type == wagon_type
                )
            )
        )
        return result.scalars().all()

class SeatRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_seat(self, seat: Seat) -> Seat:
        self.session.add(seat)
        await self.session.commit()
        await self.session.refresh(seat)
        return seat
    
    async def get_seat(self, seat_id: int) -> Optional[Seat]:
        result = await self.session.execute(select(Seat).where(Seat.id == seat_id))
        return result.scalar_one_or_none()
    
    async def get_available_seats(self, wagon_id: int) -> List[Seat]:
        result = await self.session.execute(
            select(Seat).where(
                and_(
                    Seat.wagon_id == wagon_id,
                    Seat.is_available == True,
                    Seat.is_reserved == False
                )
            ).order_by(Seat.seat_number)
        )
        return result.scalars().all()
    
    async def get_all_seats(self, wagon_id: int) -> List[Seat]:
        result = await self.session.execute(
            select(Seat).where(Seat.wagon_id == wagon_id).order_by(Seat.seat_number)
        )
        return result.scalars().all()
    
    async def update_seat_availability(self, seat_id: int, is_available: bool) -> Seat:
        seat = await self.get_seat(seat_id)
        if seat:
            seat.is_available = is_available
            await self.session.commit()
            await self.session.refresh(seat)
        return seat
    
    async def reserve_seat(self, seat_id: int) -> Seat:
        seat = await self.get_seat(seat_id)
        if seat:
            seat.is_reserved = True
            seat.is_available = False
            await self.session.commit()
            await self.session.refresh(seat)
        return seat
    
    async def release_seat(self, seat_id: int) -> Seat:
        """Освободить место (отменить резервацию)"""
        seat = await self.get_seat(seat_id)
        if seat:
            seat.is_reserved = False
            seat.is_available = True
            await self.session.commit()
            await self.session.refresh(seat)
        return seat

    async def try_reserve_seat(self, seat_id: int) -> bool:
        """Атомарная попытка забронировать место (защита от race condition)"""
        try:
            # Используем SELECT FOR UPDATE для блокировки строки
            result = await self.session.execute(
                select(Seat)
                .where(Seat.id == seat_id)
                .with_for_update()
            )
            seat = result.scalar_one_or_none()

            if not seat or not seat.is_available or seat.is_reserved:
                return False

            # Бронируем место
            seat.is_reserved = True
            seat.is_available = False
            await self.session.commit()
            return True
        except Exception:
            await self.session.rollback()
            return False

class TicketRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_ticket(self, ticket: Ticket) -> Ticket:
        self.session.add(ticket)
        await self.session.commit()
        await self.session.refresh(ticket)
        return ticket
    
    async def get_ticket(self, ticket_id: int) -> Optional[Ticket]:
        result = await self.session.execute(select(Ticket).where(Ticket.id == ticket_id))
        return result.scalar_one_or_none()
    
    async def get_ticket_by_number(self, ticket_number: str) -> Optional[Ticket]:
        result = await self.session.execute(select(Ticket).where(Ticket.ticket_number == ticket_number))
        return result.scalar_one_or_none()
    
    async def get_user_tickets(self, passenger_email: str) -> List[Ticket]:
        result = await self.session.execute(
            select(Ticket).where(Ticket.passenger_email == passenger_email).order_by(Ticket.created_at.desc())
        )
        return result.scalars().all()
    
    async def get_all_tickets(self) -> List[Ticket]:
        result = await self.session.execute(select(Ticket))
        return result.scalars().all()
    
    async def update_ticket_payment(self, ticket_id: int, is_paid: bool) -> Ticket:
        ticket = await self.get_ticket(ticket_id)
        if ticket:
            ticket.is_paid = is_paid
            await self.session.commit()
            await self.session.refresh(ticket)
        return ticket
    
    async def delete_ticket(self, ticket_id: int) -> bool:
        """Удалить билет"""
        try:
            await self.session.execute(
                delete(Ticket).where(Ticket.id == ticket_id)
            )
            await self.session.commit()
            return True
        except Exception as e:
            print(f"Error deleting ticket: {e}")
            await self.session.rollback()
            return False
    
    async def get_tickets_by_train(self, train_id: int) -> List[Ticket]:
        result = await self.session.execute(
            select(Ticket).where(Ticket.train_id == train_id)
        )
        return result.scalars().all()