#!/usr/bin/env python
"""Simple script to populate database with test trains"""
import asyncio
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Если используете SQLite, можно автоматически найти DATABASE_URL
try:
    from app.config import settings
    DATABASE_URL = settings.get_db_url
except:
    # На случай если не работает
    DATABASE_URL = "sqlite+aiosqlite:///./app.db"

print(f"📋 Database URL: {DATABASE_URL}")

async def populate():
    engine = create_async_engine(DATABASE_URL, echo=False)
    
    async with AsyncSessionLocal() as session:
        # Проверяем таблицы
        try:
            result = await session.execute(text("SELECT COUNT(*) FROM train"))
            train_count = result.scalar()
            print(f"\n🚂 Поезда в БД: {train_count}")
            
            if train_count > 0:
                print("ℹ️  Данные уже есть, пропускаем")
                return
        except Exception as e:
            print(f"ℹ️  Таблицы не существуют: {e}")
        
        # Расширенный список поездов по России
        now = datetime.now()
        trains_data = [
            # Москва - Санкт-Петербург
            ('002А', 'Москва', 'Санкт-Петербург', 2, 6, 4, 2500),
            ('004У', 'Москва', 'Санкт-Петербург', 6, 10, 4, 2200),
            ('100Ю', 'Москва', 'Санкт-Петербург', 12, 16, 4, 3000),
            ('350М', 'Санкт-Петербург', 'Москва', 3, 7, 4, 2400),
            
            # Москва - Казань
            ('016Э', 'Москва', 'Казань', 4, 16, 12, 3200),
            ('048А', 'Москва', 'Казань', 8, 20, 12, 2900),
            ('022У', 'Казань', 'Москва', 5, 17, 12, 3100),
            
            # Москва - Екатеринбург
            ('028Э', 'Москва', 'Екатеринбург', 6, 32, 26, 4500),
            ('068М', 'Москва', 'Екатеринбург', 10, 36, 26, 4200),
            ('030А', 'Екатеринбург', 'Москва', 7, 33, 26, 4400),
            
            # Москва - Нижний Новгород
            ('116Г', 'Москва', 'Нижний Новгород', 3, 10, 7, 1800),
            ('024Э', 'Москва', 'Нижний Новгород', 7, 14, 7, 1600),
            ('118Р', 'Нижний Новгород', 'Москва', 4, 11, 7, 1750),
            
            # Москва - Сочи
            ('104С', 'Москва', 'Сочи', 8, 32, 24, 5500),
            ('144С', 'Москва', 'Сочи', 12, 36, 24, 5200),
            ('102С', 'Сочи', 'Москва', 10, 34, 24, 5400),
            
            # Санкт-Петербург - Казань
            ('056Ж', 'Санкт-Петербург', 'Казань', 6, 26, 20, 3800),
            ('058К', 'Казань', 'Санкт-Петербург', 8, 28, 20, 3700),
            
            # Москва - Владивосток
            ('002М', 'Москва', 'Владивосток', 12, 156, 144, 12000),
            ('020Э', 'Владивосток', 'Москва', 14, 158, 144, 11800),
            
            # Москва - Новосибирск
            ('070Н', 'Москва', 'Новосибирск', 8, 56, 48, 6500),
            ('072Н', 'Новосибирск', 'Москва', 10, 58, 48, 6300),
            
            # Санкт-Петербург - Екатеринбург
            ('060Э', 'Санкт-Петербург', 'Екатеринбург', 9, 39, 30, 4800),
            ('062Э', 'Екатеринбург', 'Санкт-Петербург', 11, 41, 30, 4700),
            
            # Москва - Воронеж
            ('124В', 'Москва', 'Воронеж', 5, 14, 9, 2100),
            ('126В', 'Воронеж', 'Москва', 6, 15, 9, 2000),
            
            # Москва - Самара
            ('036С', 'Москва', 'Самара', 7, 21, 14, 2800),
            ('038С', 'Самара', 'Москва', 8, 22, 14, 2700),
            
            # Казань - Екатеринбург
            ('080К', 'Казань', 'Екатеринбург', 6, 20, 14, 3300),
            ('082К', 'Екатеринбург', 'Казань', 8, 22, 14, 3200),
        ]
        
        # Формируем SQL для вставки поездов
        trains_values = []
        for train in trains_data:
            number, from_city, to_city, dep_offset, arr_offset, duration, price = train
            dep_time = now + timedelta(hours=dep_offset)
            arr_time = now + timedelta(hours=arr_offset)
            trains_values.append(
                f"('{number}', '{from_city}', '{to_city}', '{dep_time}', '{arr_time}', {duration}, {price}, '{now}', '{now}')"
            )
        
        trains_sql = f"""
        INSERT INTO train (train_number, route_from, route_to, departure_time, arrival_time, duration_hours, base_price, created_at, updated_at)
        VALUES {', '.join(trains_values)}
        """
        
        try:
            await session.execute(text(trains_sql))
            await session.commit()
            print(f"✅ Добавлено {len(trains_data)} поездов")
        except Exception as e:
            print(f"❌ Ошибка при добавлении поездов: {e}")
            return
        
        # Добавляем вагоны для каждого поезда (3 типа вагонов на поезд)
        wagon_values = []
        wagon_id = 1
        for train_id in range(1, len(trains_data) + 1):
            # Плацкарт
            wagon_values.append(f"({train_id}, 'platzkart', 1, 54, 1.0, '{now}', '{now}')")
            # Купе
            wagon_values.append(f"({train_id}, 'coupe', 2, 36, 1.5, '{now}', '{now}')")
            # СВ (люкс)
            wagon_values.append(f"({train_id}, 'suite', 3, 18, 2.0, '{now}', '{now}')")
        
        wagons_sql = f"""
        INSERT INTO wagon (train_id, wagon_type, wagon_number, total_seats, price_multiplier, created_at, updated_at)
        VALUES {', '.join(wagon_values)}
        """
        
        try:
            await session.execute(text(wagons_sql))
            await session.commit()
            print(f"✅ Добавлено {len(wagon_values)} вагонов")
        except Exception as e:
            print(f"❌ Ошибка при добавлении вагонов: {e}")
            return
        
        # Добавляем места для всех вагонов
        print("🪑 Добавляем места...")
        total_wagons = len(trains_data) * 3  # 3 вагона на поезд
        
        for wagon_id in range(1, total_wagons + 1):
            # Определяем количество мест в зависимости от типа вагона
            wagon_type_index = (wagon_id - 1) % 3
            if wagon_type_index == 0:  # platzkart
                total_seats = 54
            elif wagon_type_index == 1:  # coupe
                total_seats = 36
            else:  # suite
                total_seats = 18
            
            # Добавляем все места для вагона
            seat_values = []
            for seat_num in range(1, total_seats + 1):
                seat_values.append(f"({wagon_id}, {seat_num}, 0, 1, '{now}', '{now}')")
            
            # Вставляем места пачками
            if seat_values:
                seats_sql = f"""
                INSERT INTO seat (wagon_id, seat_number, is_reserved, is_available, created_at, updated_at)
                VALUES {', '.join(seat_values)}
                """
                try:
                    await session.execute(text(seats_sql))
                except Exception as e:
                    print(f"⚠️  Ошибка при добавлении мест для вагона {wagon_id}: {e}")
        
        await session.commit()
        print("✅ Места добавлены")
        
        print("\n🎉 База данных успешно заполнена!")
        print(f"📊 Всего поездов: {len(trains_data)}")
        print(f"📊 Всего вагонов: {len(wagon_values)}")
        print(f"📊 Всего мест: ~{len(trains_data) * (54 + 36 + 18)}")
    
    await engine.dispose()

AsyncSessionLocal = sessionmaker(create_async_engine(DATABASE_URL, echo=False), class_=AsyncSession, expire_on_commit=False)

if __name__ == "__main__":
    asyncio.run(populate())
