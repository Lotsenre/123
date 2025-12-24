from datetime import datetime
from typing import AsyncGenerator

from sqlalchemy import NullPool, func, text
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    create_async_engine,
    AsyncSession,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.config import settings

engine = create_async_engine(settings.get_db_url)

engine_null_pool = create_async_engine(settings.get_db_url, poolclass=NullPool)


async_session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
async_session_maker_null_pool = async_sessionmaker(
    bind=engine_null_pool, expire_on_commit=False
)


class Base(DeclarativeBase):
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )


# Импортируем модели для регистрации в Base.metadata
# Это ВАЖНО для создания таблиц через Base.metadata.create_all()
from app.models.tickets import Train, Wagon, Seat, Ticket  # noqa: E402, F401


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Зависимость для получения асинхронной сессии БД"""
    async with async_session_maker() as session:
        yield session
