import asyncio
import httpx
from datetime import datetime, timedelta

BASE_URL = "http://127.0.0.1:8000/api/tickets"

trains_data = [
    {
        "train_number": "РЖД-001",
        "route_from": "Москва",
        "route_to": "Санкт-Петербург",
        "departure_time": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
        "arrival_time": (datetime.utcnow() + timedelta(hours=6)).isoformat(),
        "duration_hours": 4,
        "base_price": 2500.0,
        "is_active": True
    },
    {
        "train_number": "РЖД-002",
        "route_from": "Москва",
        "route_to": "Санкт-Петербург",
        "departure_time": (datetime.utcnow() + timedelta(hours=8)).isoformat(),
        "arrival_time": (datetime.utcnow() + timedelta(hours=12)).isoformat(),
        "duration_hours": 4,
        "base_price": 2000.0,
        "is_active": True
    },
    {
        "train_number": "РЖД-003",
        "route_from": "Санкт-Петербург",
        "route_to": "Москва",
        "departure_time": (datetime.utcnow() + timedelta(hours=4)).isoformat(),
        "arrival_time": (datetime.utcnow() + timedelta(hours=8)).isoformat(),
        "duration_hours": 4,
        "base_price": 2300.0,
        "is_active": True
    }
]

wagons_config = [
    {"wagon_type": "platzkart", "wagon_number": 1, "total_seats": 54, "price_multiplier": 1.0},
    {"wagon_type": "coupe", "wagon_number": 2, "total_seats": 36, "price_multiplier": 1.5},
    {"wagon_type": "suite", "wagon_number": 3, "total_seats": 18, "price_multiplier": 2.0}
]

async def create_trains():
    async with httpx.AsyncClient(timeout=10.0) as client:
        for train_data in trains_data:
            try:
                print(f"\n🚂 Создаю поезд: {train_data['train_number']}")
                resp = await client.post(f"{BASE_URL}/trains", json=train_data)
                
                if resp.status_code != 200:
                    print(f"❌ Ошибка: {resp.status_code}")
                    print(resp.text[:300])
                    continue
                
                train = resp.json()
                train_id = train.get('id')
                print(f"✅ Поезд создан (ID: {train_id})")
                
                # Создаем вагоны
                for wagon_cfg in wagons_config:
                    wagon_data = {**wagon_cfg, "train_id": train_id}
                    try:
                        wagon_resp = await client.post(f"{BASE_URL}/wagons", json=wagon_data)
                        if wagon_resp.status_code == 200:
                            wagon = wagon_resp.json()
                            print(f"  ✅ {wagon_cfg['wagon_type'].upper()}: {wagon_cfg['total_seats']} мест (ID: {wagon.get('id')})")
                        else:
                            print(f"  ❌ Ошибка вагона: {wagon_resp.status_code}")
                    except Exception as e:
                        print(f"  ❌ Ошибка: {e}")
                        
            except Exception as e:
                print(f"❌ Ошибка при создании поезда: {e}")

async def main():
    print("\n" + "="*60)
    print("🚂 ИНИЦИАЛИЗАЦИЯ ТЕСТОВЫХ БИЛЕТОВ")
    print("="*60)
    print(f"\n📍 Подключаюсь к: {BASE_URL}\n")
    
    try:
        await create_trains()
        print("\n" + "="*60)
        print("✨ ГОТОВО! Билеты добавлены в БД")
        print("="*60)
        print("\n🔍 Чтобы проверить:")
        print("  1. Открой http://127.0.0.1:8000")
        print("  2. Залогинься")
        print("  3. Ищи билеты: Москва → Санкт-Петербург")
        print("\n")
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        print("\n⚠️  Убедись, что uvicorn запущен:")
        print("   $ uvicorn main:app")

if __name__ == "__main__":
    asyncio.run(main())
