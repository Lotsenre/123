import uvicorn
import logging
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from contextlib import asynccontextmanager

from app.api.sample import router as sample_router
from app.api.auth import router as auth_router
from app.api.roles import router as role_router
from app.api.tickets import router as tickets_router
from app.database.database import Base, engine
from app.services.auth import AuthService
from app.exceptions.auth import InvalidJWTTokenError, JWTTokenExpiredError

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Жизненный цикл приложения
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup - создание таблиц при запуске
    logger.info("🚀 Создание таблиц базы данных...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Таблицы успешно созданы")
    
    # Здесь выполняется основной код приложения
    yield
    
    # Shutdown - очистка при выключении
    logger.info("💤 Приложение останавливается...")
    await engine.dispose()
    logger.info("✅ Соединение с БД закрыто")

app = FastAPI(
    title="ВагоноМесто - Сервис покупки ж/д билетов",
    version="1.0.0",
    description="Онлайн платформа для бронирования железнодорожных билетов",
    lifespan=lifespan
)

# CORS
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware для проверки аутентификации на API routes
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    # Пропускаем auth routes, static files и public endpoints
    if (request.url.path.startswith("/api/auth") or 
        request.url.path.startswith("/static") or 
        request.url.path == "/" or 
        request.url.path == "" or 
        request.url.path == "/health" or
        request.url.path.startswith("/admin") or  # SQLAdmin routes
        # Разрешаем публичные эндпоинты для поиска и информации
        request.url.path.startswith("/api/tickets/trains/search") or
        request.url.path.startswith("/api/tickets/trains") or
        request.url.path.startswith("/api/tickets/discounts")):
        return await call_next(request)
    
    # Для остальных API routes проверяем токен
    if request.url.path.startswith("/api/"):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return FileResponse(
                Path(__file__).parent / "app" / "static" / "index.html",
                status_code=200
            )
        
        token = auth_header.replace("Bearer ", "")
        try:
            AuthService.decode_token(token)
        except (InvalidJWTTokenError, JWTTokenExpiredError):
            return FileResponse(
                Path(__file__).parent / "app" / "static" / "index.html",
                status_code=200
            )
    
    return await call_next(request)

# Маршруты API
app.include_router(sample_router)
app.include_router(auth_router)
app.include_router(role_router)
app.include_router(tickets_router)

# Статические файлы
static_dir = Path(__file__).parent / "app" / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    logger.info(f"✅ Статические файлы найдены в {static_dir}")
else:
    logger.warning(f"⚠️ Директория статических файлов не найдена: {static_dir}")

# SQLAdmin - опциональная интеграция
try:
    from sqladmin import Admin, ModelView
    from sqladmin.authentication import AuthenticationBackend
    from app.models.users import UserModel
    from app.models.tickets import Train, Wagon, Seat, Ticket
    from app.models.roles import RoleModel
    
    # SQLAdmin Authentication
    class AdminAuth(AuthenticationBackend):
        async def login(self, username: str, password: str, request: Request) -> bool:
            # Простая аутентификация с фиксированным паролем
            return password == "01020304"

        async def logout(self, request: Request) -> bool:
            request.session.clear()
            return True

        async def authenticate(self, request: Request) -> bool:
            token = request.session.get("admin_token")
            return token == "admin_authenticated"
    
    # SQLAdmin ModelViews
    class UserAdmin(ModelView, model=UserModel):
        name = "Пользователь"
        name_plural = "Пользователи"
        column_list = [UserModel.id, UserModel.email, UserModel.name, UserModel.created_at]
        column_exclude_list = [UserModel.hashed_password]

    class TrainAdmin(ModelView, model=Train):
        name = "Поезд"
        name_plural = "Поезда"
        column_list = [Train.id, Train.train_number, Train.route_from, Train.route_to, 
                       Train.departure_time, Train.arrival_time]

    class WagonAdmin(ModelView, model=Wagon):
        name = "Вагон"
        name_plural = "Вагоны"
        column_list = [Wagon.id, Wagon.train_id, Wagon.wagon_number, Wagon.wagon_type]

    class SeatAdmin(ModelView, model=Seat):
        name = "Место"
        name_plural = "Места"
        column_list = [Seat.id, Seat.wagon_id, Seat.seat_number, Seat.is_reserved]

    class TicketAdmin(ModelView, model=Ticket):
        name = "Билет"
        name_plural = "Билеты"
        column_list = [Ticket.id, Ticket.ticket_number, Ticket.train_id, Ticket.seat_id,
                       Ticket.passenger_name, Ticket.passenger_email, Ticket.final_price]

    class RoleAdmin(ModelView, model=RoleModel):
        name = "Роль"
        name_plural = "Роли"
        column_list = [RoleModel.id, RoleModel.name]
    
    # Регистрация SQLAdmin
    admin = Admin(
        app=app,
        engine=engine,
        title="Админ Панель - ВагоноМесто",
        logo_url="https://cdn-icons-png.flaticon.com/512/4641/4641073.png",
        authentication_backend=AdminAuth()
    )
    
    admin.add_view(UserAdmin)
    admin.add_view(TrainAdmin)
    admin.add_view(WagonAdmin)
    admin.add_view(SeatAdmin)
    admin.add_view(TicketAdmin)
    admin.add_view(RoleAdmin)
    
    logger.info("✅ SQLAdmin зарегистрирован на /admin")
    logger.info("🔐 Пароль для входа: 01020304")
    
except ImportError as e:
    logger.warning(f"⚠️ SQLAdmin не установлен или ошибка импорта: {e}")
    logger.info("🚀 Подсказка: pip install sqladmin")

# Главная страница - всегда возвращает index.html (фронтенд сам будет проверять токен)
@app.get("/")
async def root():
    html_file = static_dir / "index.html"
    if html_file.exists():
        return FileResponse(html_file)
    return {"message": "Добро пожаловать в ВагоноМесто!"}

# Health check
@app.get("/health")
async def health():
    return {"status": "ok", "service": "wagono-mesto"}

if __name__ == "__main__":
    logger.info("🚂 Запуск сервера ВагоноМесто...")
    uvicorn.run(
        app=app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
