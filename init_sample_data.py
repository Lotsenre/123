"""Скрипт для инициализации тестовых данных в БД"""
import asyncio
import httpx
from datetime import datetime, timedelta

BASE_URL = "http://127.0.0.1:8000/api/tickets"

async def create_sample_trains():
    """Создать тестовые поезда"""
    
    trains = [
        {
            "train_number": "РЖД-001",
            "route_from": "Москва",
            "route_to": "Санкт-Петербург",
            "departure_time": (datetime.now() + timedelta(hours=2)).isoformat(),
            "arrival_time": (datetime.now() + timedelta(hours=6)).isoformat(),
            "duration_hours": 4,
            "base_price": 2500
        },
        {
            "train_number": "РЖД-002",
            "route_from": "Москва",
            "route_to": "Санкт-Петербург",
            "departure_time": (datetime.now() + timedelta(hours=8)).isoformat(),
            "arrival_time": (datetime.now() + timedelta(hours=12)).isoformat(),
            "duration_hours": 4,
            "base_price": 2000
        },
        {
            "train_number": "РЖД-003",
            "route_from": "Санкт-Петербург",
            "route_to": "Москва",
            "departure_time": (datetime.now() + timedelta(hours=4)).isoformat(),
            "arrival_time": (datetime.now() + timedelta(hours=8)).isoformat(),
            "duration_hours": 4,
            "base_price": 2300
        },
        {
            "train_number": "РЖД-004",
            "route_from": "Москва",
            "route_to": "Екатеринбург",
            "departure_time": (datetime.now() + timedelta(hours=12)).isoformat(),
            "arrival_time": (datetime.now() + timedelta(days=1, hours=4)).isoformat(),
            "duration_hours": 28,
            "base_price": 5000
        }
    ]
    
    async with httpx.AsyncClient() as client:
        for train_data in trains:
            try:
                response = await client.post(f"{BASE_URL}/trains", json=train_data)
                if response.status_code == 200:
                    train = response.json()
                    print(f"✅ Поезд создан: {train['train_number']} (ID: {train.get('id')})")
                    
                    # Создать вагоны для поезда
                    await create_wagons_for_train(client, train['id'])
                else:
                    print(f"❌ Ошибка при создании поезда: {response.status_code}")
                    print(response.text)
            except Exception as e:
                print(f"❌ Ошибка при создании поезда: {e}")

async def create_wagons_for_train(client: httpx.AsyncClient, train_id: int):
    """Создать вагоны для поезда"""
    
    wagons = [
        {
            "train_id": train_id,
            "wagon_type": "platzkart",
            "wagon_number": 1,
            "total_seats": 54,
            "price_multiplier": 1.0
        },
        {
            "train_id": train_id,
            "wagon_type": "coupe",
            "wagon_number": 2,
            "total_seats": 36,
            "price_multiplier": 1.5
        },
        {
            "train_id": train_id,
            "wagon_type": "suite",
            "wagon_number": 3,
            "total_seats": 18,
            "price_multiplier": 2.0
        }
    ]
    
    for wagon_data in wagons:
        try:
            response = await client.post(f"{BASE_URL}/wagons", json=wagon_data)
            if response.status_code == 200:
                wagon = response.json()
                print(f"  ✅ Вагон создан: {wagon_data['wagon_type'].upper()} (ID: {wagon.get('id')})")
            else:
                print(f"  ❌ Ошибка при создании вагона: {response.status_code}")
        except Exception as e:
            print(f"  ❌ Ошибка при создании вагона: {e}")

async def main():
    print("🚂 Начинаю инициализацию тестовых данных...\n")
    await create_sample_trains()
    print("\n✨ Инициализация завершена!")
    print("\nТеперь ты можешь:")
    print("1. Открыть http://127.0.0.1:8000")
    print("2. Зарегистрироваться/логиниться")
    print("3. Поиск билетов - Москва -> Санкт-Петербург")
    print("4. Выбрать поезд и оформить билет")

if __name__ == "__main__":
    asyncio.run(main())
