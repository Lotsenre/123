import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from app.api.sample import router as sample_router
from app.api.auth import router as auth_router
from app.api.roles import router as role_router
from app.api.tickets import router as tickets_router
from app.database.database import Base, engine

app = FastAPI(
    title="ВагоноМесто - Сервис покупки ж/д билетов",
    version="1.0.0",
    description="Онлайн платформа для бронирования железнодорожных билетов"
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

# Создание таблиц при запуске
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Маршруты API
app.include_router(sample_router)
app.include_router(auth_router)
app.include_router(role_router)
app.include_router(tickets_router)

# Статические файлы
static_dir = Path(__file__).parent / "app" / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Главная страница
@app.get("/")
async def root():
    return FileResponse(static_dir / "index.html")

if __name__ == "__main__":
    uvicorn.run(app=app, host="0.0.0.0", port=8000)
