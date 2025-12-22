import uvicorn
import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from contextlib import asynccontextmanager

from app.api.sample import router as sample_router
from app.api.auth import router as auth_router
from app.api.roles import router as role_router
from app.api.tickets import router as tickets_router
from app.database.database import Base, engine

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

# Главная страница
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
