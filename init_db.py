"""Script to initialize database with default roles.
Run this before first use: python init_db.py
"""
import asyncio
from sqlalchemy import select

# IMPORTANT: Import all models first to register them
from app.models.roles import RoleModel
from app.models.users import UserModel
from app.models.tickets import TrainModel, WagonModel, SeatModel, TicketModel

from app.database.database import Base, engine, async_session_maker


async def init_db():
    """Create all tables and insert default roles."""
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print("✅ Новые таблицы созданы")
    
    # Create default roles
    async with async_session_maker() as session:
        # Check if roles exist
        result = await session.execute(select(RoleModel))
        existing_roles = result.scalars().all()
        
        if not existing_roles:
            print("🚁 Роли не найдены, создаю дефолтные...")
            
            # Create default roles
            roles = [
                RoleModel(id=1, name="user"),
                RoleModel(id=2, name="admin"),
                RoleModel(id=3, name="moderator"),
            ]
            
            for role in roles:
                session.add(role)
            
            await session.commit()
            print("✅ Дефолтные роли созданы:")
            print("  - user (пользователь)")
            print("  - admin (администратор)")
            print("  - moderator (модератор)")
        else:
            print("✅ Роли уже существуют:")
            for role in existing_roles:
                print(f"  - {role.name} (id={role.id})")
    
    await engine.dispose()
    print("🌟 База данных инициализирована до 100%")


if __name__ == "__main__":
    asyncio.run(init_db())
