from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from datetime import datetime
import logging

from app.database.database import get_async_session
from app.models.tickets import Train, Wagon, Seat, Ticket
from app.api.dependencies import UserIdDep, DBDep, AdminDep
from app.schemes.ticket_schemes import (
    TrainCreate, TrainResponse, TrainScheduleResponse,
    WagonCreate, WagonResponse, WagonWithSeatsResponse,
    SeatResponse,
    TicketCreate, TicketResponse, TicketDetailResponse,
    SearchRequest,
    PriceCalculationRequest, PriceCalculationResponse,
    PaymentRequest, PaymentResponse, WagonTypeEnum
)
from app.repositories.ticket_repository import (
    TrainRepository, WagonRepository, SeatRepository, TicketRepository
)
from app.services.ticket_service import (
    TrainService, WagonService, SeatService, TicketService, DiscountService
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tickets", tags=["Tickets"])

# Зависимости
async def get_train_service(session: AsyncSession = Depends(get_async_session)) -> TrainService:
    return TrainService(TrainRepository(session))

async def get_wagon_service(session: AsyncSession = Depends(get_async_session)) -> WagonService:
    return WagonService(WagonRepository(session), SeatRepository(session))

async def get_seat_service(session: AsyncSession = Depends(get_async_session)) -> SeatService:
    return SeatService(SeatRepository(session))

async def get_ticket_service(session: AsyncSession = Depends(get_async_session)) -> TicketService:
    return TicketService(TicketRepository(session), SeatRepository(session))

# ============= МАРШРУТЫ ПОЕЗДОВ =============

@router.post("/trains", response_model=TrainResponse, summary="Создать новый поезд")
async def create_train(
    train_data: TrainCreate,
    admin_id: AdminDep,  # Только для админов
    service: TrainService = Depends(get_train_service)
):
    """Создать новый поезд в системе (только для администраторов)"""
    return await service.create_train(train_data)

@router.get("/trains/search", response_model=List[TrainScheduleResponse], summary="Поиск поездов")
async def search_trains(
    route_from: str,
    route_to: str,
    train_service: TrainService = Depends(get_train_service),
    wagon_service: WagonService = Depends(get_wagon_service),
    seat_service: SeatService = Depends(get_seat_service)
):
    """Поиск доступных поездов по маршруту"""
    # Валидация входных данных
    if not route_from or not route_from.strip():
        raise HTTPException(status_code=400, detail="Укажите город отправления")
    if not route_to or not route_to.strip():
        raise HTTPException(status_code=400, detail="Укажите город прибытия")
    if len(route_from) > 100 or len(route_to) > 100:
        raise HTTPException(status_code=400, detail="Название города слишком длинное")

    trains = await train_service.search_trains(route_from.strip(), route_to.strip())

    result = []
    for train in trains:
        wagons = await wagon_service.get_wagons_by_train(train.id)
        wagon_responses = []
        available_seats = 0

        for wagon in wagons:
            available = await seat_service.count_available_seats(wagon.id)
            available_seats += available
            wagon_responses.append(WagonResponse.model_validate(wagon))

        result.append(TrainScheduleResponse(
            id=train.id,
            train_number=train.train_number,
            route_from=train.route_from,
            route_to=train.route_to,
            departure_time=train.departure_time,
            arrival_time=train.arrival_time,
            duration_hours=train.duration_hours,
            base_price=train.base_price,
            available_seats_count=available_seats,
            wagons=wagon_responses
        ))

    return result

@router.get("/trains/{train_id}", response_model=TrainResponse, summary="Получить информацию о поезде")
async def get_train(
    train_id: int,
    service: TrainService = Depends(get_train_service)
):
    """Получить информацию о конкретном поезде"""
    train = await service.get_train(train_id)
    if not train:
        raise HTTPException(status_code=404, detail="Поезд не найден")
    return train

@router.get("/trains", response_model=List[TrainResponse], summary="Получить все поезда")
async def get_all_trains(
    service: TrainService = Depends(get_train_service)
):
    """Получить список всех активных поездов"""
    return await service.get_all_trains()

# ============= МАРШРУТЫ ВАГОНОВ =============

@router.post("/wagons", response_model=WagonResponse, summary="Создать вагон")
async def create_wagon(
    wagon_data: WagonCreate,
    admin_id: AdminDep,  # Только для админов
    wagon_service: WagonService = Depends(get_wagon_service),
    seat_service: SeatService = Depends(get_seat_service)
):
    """Создать новый вагон (только для администраторов)"""
    wagon = await wagon_service.create_wagon(wagon_data)
    # Создать места для вагона
    await seat_service.create_seats(wagon.id, wagon.total_seats)
    return wagon

@router.get("/wagons/{wagon_id}", response_model=WagonWithSeatsResponse, summary="Получить схему вагона")
async def get_wagon(
    wagon_id: int,
    wagon_service: WagonService = Depends(get_wagon_service),
    seat_service: SeatService = Depends(get_seat_service)
):
    """Получить информацию о вагоне со всеми местами"""
    wagon = await wagon_service.get_wagon(wagon_id)
    if not wagon:
        raise HTTPException(status_code=404, detail="Вагон не найден")

    seats = await seat_service.get_wagon_layout(wagon_id)
    return WagonWithSeatsResponse(
        **{k: getattr(wagon, k) for k in WagonResponse.model_fields},
        seats=[SeatResponse.model_validate(seat) for seat in seats]
    )

@router.get("/trains/{train_id}/wagons", response_model=List[WagonResponse], summary="Получить вагоны поезда")
async def get_train_wagons(
    train_id: int,
    service: WagonService = Depends(get_wagon_service)
):
    """Получить все вагоны поезда"""
    return await service.get_wagons_by_train(train_id)

@router.get("/trains/{train_id}/wagons/type/{wagon_type}", response_model=List[WagonResponse], summary="Получить вагоны по типу")
async def get_wagons_by_type(
    train_id: int,
    wagon_type: WagonTypeEnum,
    service: WagonService = Depends(get_wagon_service)
):
    """Получить вагоны конкретного типа (platzkart, coupe, suite)"""
    wagons = await service.get_wagons_by_type(train_id, wagon_type.value)
    if not wagons:
        raise HTTPException(status_code=404, detail="Вагоны не найдены")
    return wagons

# ============= МАРШРУТЫ МЕСТ =============

@router.get("/wagons/{wagon_id}/layout", response_model=List[SeatResponse], summary="Получить схему мест вагона")
async def get_wagon_layout(
    wagon_id: int,
    service: SeatService = Depends(get_seat_service)
):
    """Получить визуальную схему всех мест в вагоне"""
    seats = await service.get_wagon_layout(wagon_id)
    if not seats:
        raise HTTPException(status_code=404, detail="Вагон не найден или нет мест")
    return [SeatResponse.model_validate(seat) for seat in seats]

@router.get("/wagons/{wagon_id}/available", response_model=List[SeatResponse], summary="Свободные места")
async def get_available_seats(
    wagon_id: int,
    service: SeatService = Depends(get_seat_service)
):
    """Получить список свободных мест в вагоне"""
    seats = await service.get_available_seats(wagon_id)
    return [SeatResponse.model_validate(seat) for seat in seats]

# ============= МАРШРУТЫ РАСЧЕТА ЦЕНЫ И СКИДОК =============

@router.post("/calculate-price", response_model=PriceCalculationResponse, summary="Расчет стоимости билета")
async def calculate_price(
    request: PriceCalculationRequest,
    train_service: TrainService = Depends(get_train_service),
    wagon_service: WagonService = Depends(get_wagon_service),
    ticket_service: TicketService = Depends(get_ticket_service)
):
    """Рассчитать стоимость билета с учетом скидок"""
    train = await train_service.get_train(request.train_id)
    if not train:
        raise HTTPException(status_code=404, detail="Поезд не найден")

    wagon = await wagon_service.get_wagon(request.wagon_id)
    if not wagon:
        raise HTTPException(status_code=404, detail="Вагон не найден")

    return await ticket_service.calculate_price(train, wagon, request.discount_type.value)

@router.get("/discounts", summary="Информация о скидках")
async def get_discounts():
    """Получить информацию о доступных скидках"""
    return {
        "discounts": [
            {"type": "child", "description": "Детская скидка (0-12 лет)", "percent": 50},
            {"type": "student", "description": "Студенческая скидка", "percent": 25},
            {"type": "pensioner", "description": "Пенсионная скидка", "percent": 40},
            {"type": "none", "description": "Без скидки", "percent": 0}
        ]
    }

# ============= МАРШРУТЫ БИЛЕТОВ =============

@router.get("/my-tickets", response_model=List[TicketResponse], summary="Мои билеты")
async def get_my_tickets(
    user_id: UserIdDep,
    db: DBDep,
    service: TicketService = Depends(get_ticket_service)
):
    """Получить все билеты текущего пользователя"""
    # Получаем email пользователя по user_id
    user = await db.users.get_one_or_none(id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    tickets = await service.get_user_tickets(user.email)
    return tickets

@router.post("/create", response_model=TicketResponse, summary="Создать и забронировать билет")
async def create_ticket(
    ticket_data: TicketCreate,
    user_id: UserIdDep,
    db: DBDep,
    train_service: TrainService = Depends(get_train_service),
    wagon_service: WagonService = Depends(get_wagon_service),
    seat_service: SeatService = Depends(get_seat_service),
    ticket_service: TicketService = Depends(get_ticket_service)
):
    """Создать новый билет и зарезервировать место"""
    # Получаем данные пользователя для проверки email
    user = await db.users.get_one_or_none(id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    # Проверяем, что пользователь создаёт билет на свой email
    if ticket_data.passenger_email != user.email:
        raise HTTPException(
            status_code=403,
            detail="Вы можете создавать билеты только на свой email"
        )

    # Проверить поезд
    train = await train_service.get_train(ticket_data.train_id)
    if not train:
        raise HTTPException(status_code=404, detail="Поезд не найден")

    # Проверить вагон
    wagon = await wagon_service.get_wagon(ticket_data.wagon_id)
    if not wagon:
        raise HTTPException(status_code=404, detail="Вагон не найден")

    # Атомарная проверка и резервирование места (исправление race condition)
    seat_reserved = await seat_service.try_reserve_seat(ticket_data.seat_id)
    if not seat_reserved:
        raise HTTPException(status_code=400, detail="Место недоступно для бронирования")

    try:
        # Рассчитать цену
        price_calc = await ticket_service.calculate_price(train, wagon, ticket_data.discount_type.value)

        # Создать билет
        ticket = await ticket_service.create_ticket(
            ticket_data,
            price_calc.base_price,
            price_calc.final_price,
            train
        )

        return TicketResponse.model_validate(ticket)
    except Exception as e:
        # Если что-то пошло не так - освобождаем место
        await seat_service.release_seat(ticket_data.seat_id)
        logger.error(f"Ошибка создания билета: {e}")
        raise HTTPException(status_code=500, detail="Ошибка при создании билета")

@router.get("/ticket/{ticket_id}", response_model=TicketResponse, summary="Получить информацию о билете")
async def get_ticket(
    ticket_id: int,
    user_id: UserIdDep,
    db: DBDep,
    service: TicketService = Depends(get_ticket_service)
):
    """Получить информацию о конкретном билете (только свои билеты)"""
    ticket = await service.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Билет не найден")

    # Проверяем владельца билета
    user = await db.users.get_one_or_none(id=user_id)
    if not user or ticket.passenger_email != user.email:
        raise HTTPException(status_code=403, detail="Доступ к билету запрещён")

    return ticket

@router.get("/user/{passenger_email}", response_model=List[TicketResponse], summary="Билеты пассажира")
async def get_user_tickets(
    passenger_email: str,
    user_id: UserIdDep,
    db: DBDep,
    service: TicketService = Depends(get_ticket_service)
):
    """Получить все билеты пассажира (только свои билеты)"""
    # Проверяем, что пользователь запрашивает свои билеты
    user = await db.users.get_one_or_none(id=user_id)
    if not user or user.email != passenger_email:
        raise HTTPException(status_code=403, detail="Вы можете просматривать только свои билеты")

    return await service.get_user_tickets(passenger_email)

@router.delete("/delete/{ticket_id}", summary="Удалить билет")
async def delete_ticket(
    ticket_id: int,
    user_id: UserIdDep,
    db: DBDep,
    seat_service: SeatService = Depends(get_seat_service),
    ticket_service: TicketService = Depends(get_ticket_service)
):
    """Удалить билет и освободить место (только свои билеты)"""
    ticket = await ticket_service.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Билет не найден")

    # Проверяем владельца билета
    user = await db.users.get_one_or_none(id=user_id)
    if not user or ticket.passenger_email != user.email:
        raise HTTPException(status_code=403, detail="Вы можете удалять только свои билеты")

    # Освободить место
    await seat_service.release_seat(ticket.seat_id)

    # Удалить билет
    await ticket_service.delete_ticket(ticket_id)

    return {"message": "Билет успешно удален", "ticket_id": ticket_id}

@router.post("/pay", response_model=TicketResponse, summary="Оплатить билет")
async def pay_ticket(
    payment: PaymentRequest,
    user_id: UserIdDep,
    db: DBDep,
    service: TicketService = Depends(get_ticket_service)
):
    """Оплатить билет (только свои билеты)"""
    ticket = await service.get_ticket(payment.ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Билет не найден")

    # Проверяем владельца билета
    user = await db.users.get_one_or_none(id=user_id)
    if not user or ticket.passenger_email != user.email:
        raise HTTPException(status_code=403, detail="Вы можете оплачивать только свои билеты")

    ticket = await service.pay_ticket(payment.ticket_id)
    return ticket

@router.get("/ticket/{ticket_id}/pdf", summary="Получить электронный билет")
async def get_ticket_pdf(
    ticket_id: int,
    user_id: UserIdDep,
    db: DBDep,
    train_service: TrainService = Depends(get_train_service),
    wagon_service: WagonService = Depends(get_wagon_service),
    seat_service: SeatService = Depends(get_seat_service),
    ticket_service: TicketService = Depends(get_ticket_service)
):
    """Получить данные для электронного билета в формате JSON (только свои билеты)"""
    ticket = await ticket_service.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Билет не найден")

    # Проверяем владельца билета
    user = await db.users.get_one_or_none(id=user_id)
    if not user or ticket.passenger_email != user.email:
        raise HTTPException(status_code=403, detail="Вы можете скачивать только свои билеты")

    train = await train_service.get_train(ticket.train_id)
    wagon = await wagon_service.get_wagon(ticket.wagon_id)
    seat = await seat_service.get_seat(ticket.seat_id)

    return await ticket_service.generate_pdf_ticket(ticket, train, wagon, seat)
