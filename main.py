import uvicorn
import logging
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path
from contextlib import asynccontextmanager
from starlette.middleware.sessions import SessionMiddleware

from app.api.sample import router as sample_router
from app.api.auth import router as auth_router
from app.api.roles import router as role_router
from app.api.tickets import router as tickets_router
from app.database.database import Base, engine, async_session_maker
from app.models.roles import RoleModel
from sqlalchemy import select
from app.services.auth import AuthService
from app.exceptions.auth import InvalidJWTTokenError, JWTTokenExpiredError
from app.config import settings

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

    # Создание ролей по умолчанию
    async with async_session_maker() as session:
        result = await session.execute(select(RoleModel))
        existing_roles = result.scalars().all()
        if not existing_roles:
            logger.info("📋 Создание ролей по умолчанию...")
            session.add(RoleModel(id=1, name="user"))
            session.add(RoleModel(id=2, name="admin"))
            session.add(RoleModel(id=3, name="moderator"))
            await session.commit()
            logger.info("✅ Роли созданы")

    # Здесь выполняется основной код приложения
    yield

    # Shutdown - очистка при выключении
    logger.info("😴 Приложение останавливается...")
    await engine.dispose()
    logger.info("✅ Соединение с БД закрыто")

app = FastAPI(
    title="ВагоноМесто - Сервис покупки ж/д билетов",
    version="1.0.0",
    description="Онлайн платформа для бронирования железнодорожных билетов",
    lifespan=lifespan
)

# Middleware
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SessionMiddleware, secret_key=settings.SESSION_SECRET)

# Аутентификация реализована через dependencies в tickets.py
# Публичные маршруты не требуют токена, защищённые используют CurrentUserDep

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

# SQLAdmin с аутентификацией
try:
    from sqladmin import Admin, ModelView
    from sqladmin.authentication import AuthenticationBackend
    from starlette.requests import Request as StarletteRequest
    from starlette.responses import RedirectResponse
    from app.models.users import UserModel
    from app.models.tickets import Train, Wagon, Seat, Ticket
    from app.models.roles import RoleModel

    # Аутентификация для админ-панели
    class AdminAuth(AuthenticationBackend):
        async def login(self, request: StarletteRequest) -> bool:
            form = await request.form()
            username = form.get("username")
            password = form.get("password")

            # Проверяем логин/пароль из конфига
            if username == settings.ADMIN_USERNAME and password == settings.ADMIN_PASSWORD:
                request.session.update({"admin_authenticated": True})
                return True
            return False

        async def logout(self, request: StarletteRequest) -> bool:
            request.session.clear()
            return True

        async def authenticate(self, request: StarletteRequest) -> bool:
            return request.session.get("admin_authenticated", False)

    # SQLAdmin ModelViews
    class UserAdmin(ModelView, model=UserModel):
        name = "Пользователь"
        name_plural = "Пользователи"
        column_exclude_list = [UserModel.hashed_password]
        page_size = 10
        page_size_options = [10, 25, 50]

    class TrainAdmin(ModelView, model=Train):
        name = "Поезд"
        name_plural = "Поезда"
        page_size = 10
        page_size_options = [10, 25, 50]
        can_delete = False

    class WagonAdmin(ModelView, model=Wagon):
        name = "Вагон"
        name_plural = "Вагоны"
        page_size = 10
        page_size_options = [10, 25, 50]

    class SeatAdmin(ModelView, model=Seat):
        name = "Место"
        name_plural = "Места"
        page_size = 20
        page_size_options = [10, 20, 50]

    class TicketAdmin(ModelView, model=Ticket):
        name = "Билет"
        name_plural = "Билеты"
        page_size = 10
        page_size_options = [10, 25, 50]
        column_exclude_list = []

    class RoleAdmin(ModelView, model=RoleModel):
        name = "Роль"
        name_plural = "Роли"
        page_size = 10
        page_size_options = [10, 25, 50]

    # Регистрация SQLAdmin С аутентификацией
    authentication_backend = AdminAuth(secret_key=settings.SESSION_SECRET)
    admin = Admin(
        app=app,
        engine=engine,
        title="Админ Панель - ВагоноМесто",
        logo_url="https://cdn-icons-png.flaticon.com/512/4641/4641073.png",
        authentication_backend=authentication_backend
    )

    admin.add_view(UserAdmin)
    admin.add_view(TrainAdmin)
    admin.add_view(WagonAdmin)
    admin.add_view(SeatAdmin)
    admin.add_view(TicketAdmin)
    admin.add_view(RoleAdmin)

    logger.info("✅ SQLAdmin зарегистрирован на /admin")
    logger.info("🔐 Админ панель защищена паролем (логин: admin)")

except Exception as e:
    logger.error(f"❌ Ошибка SQLAdmin: {e}")
    import traceback
    traceback.print_exc()

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
    # reload=True требует указания модуля как строки, иначе кеширует старый код
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
