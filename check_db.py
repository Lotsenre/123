"""Скрипт для проверки содержимого БД"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text

from app.config import settings
from app.models.tickets import Train, Wagon, Seat

engine = create_async_engine(settings.get_db_url, echo=False)
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def check_db():
    """Проверить содержимое БД"""
    
    async with AsyncSessionLocal() as session:
        # Проверяем поезда
        result = await session.execute(select(Train))
        trains = result.scalars().all()
        
        print(f"\n🚂 ПОЕЗДА В БД: {len(trains)}")
        for train in trains:
            print(f"   ID: {train.id} | Номер: {train.train_number} | {train.route_from} → {train.route_to}")
        
        # Проверяем вагоны
        result = await session.execute(select(Wagon))
        wagons = result.scalars().all()
        
        print(f"\n🚪 ВАГОНЫ В БД: {len(wagons)}")
        for wagon in wagons:
            print(f"   ID: {wagon.id} | Поезд: {wagon.train_id} | Тип: {wagon.wagon_type} | Мест: {wagon.total_seats}")
        
        # Проверяем места
        result = await session.execute(select(Seat))
        seats = result.scalars().all()
        
        print(f"\n🪑 МЕСТА В БД: {len(seats)}")
        
        # Проверяем структуру таблиц
        print("\n📋 СТРУКТУРА ТАБЛИЦ:")
        
        try:
            # Информация о таблице trains
            result = await session.execute(text("PRAGMA table_info(train);"))
            rows = result.fetchall()
            if rows:
                print("\n   Таблица 'train':")
                for row in rows:
                    print(f"      {row}")
        except:
            pass
        
        if not trains and not wagons and not seats:
            print("\n❌ БД ПУСТА! Нужно запустить init_db.py")
        else:
            print(f"\n✅ БД содержит данные")

async def main():
    try:
        await check_db()
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
