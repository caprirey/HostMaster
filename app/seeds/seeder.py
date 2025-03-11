from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.sqlalchemy_models import (
    Country, State, City, Accommodation, RoomType, Room, UserTable, Reservation
)
from app.utils.auth import get_password_hash
from datetime import date

async def seed_database(db: AsyncSession):
    result = await db.execute(select(UserTable))
    if result.scalars().first():
        print("Database already seeded, skipping...")
        return

    # Usuarios
    admin_user = UserTable(
        username="admin",
        email="admin@hotel.com",
        full_name="Admin User",
        hashed_password=get_password_hash("admin"),
        disabled=False,
        role="admin"
    )
    user1 = UserTable(
        username="user1",
        email="user1@hotel.com",
        full_name="User One",
        hashed_password=get_password_hash("user1"),
        disabled=False,
        role="user"
    )
    db.add_all([admin_user, user1])
    await db.flush()

    # Países
    spain = Country(name="Spain")
    db.add(spain)
    await db.flush()

    # Estados
    madrid_state = State(name="Madrid", country_id=spain.id)
    db.add(madrid_state)
    await db.flush()

    # Ciudades
    madrid_city = City(name="Madrid", state_id=madrid_state.id)
    db.add(madrid_city)
    await db.flush()

    # Alojamientos
    hotel_sol = Accommodation(name="Hotel Sol", city_id=madrid_city.id, created_by="admin")
    hotel_luna = Accommodation(name="Hotel Luna", city_id=madrid_city.id, created_by="user1")
    db.add_all([hotel_sol, hotel_luna])
    await db.flush()

    # Tipos de habitación
    single_room_type = RoomType(name="Single")
    double_room_type = RoomType(name="Double")
    db.add_all([single_room_type, double_room_type])
    await db.flush()

    # Habitaciones
    room_101 = Room(accommodation_id=hotel_sol.id, type_id=single_room_type.id, number="101")
    room_201 = Room(accommodation_id=hotel_luna.id, type_id=double_room_type.id, number="201")
    db.add_all([room_101, room_201])
    await db.flush()

    # Reservas
    reservation_1 = Reservation(
        user_username="admin",
        room_id=room_101.id,
        start_date=date(2025, 3, 15),
        end_date=date(2025, 3, 20)
    )
    reservation_2 = Reservation(
        user_username="user1",
        room_id=room_201.id,
        start_date=date(2025, 3, 16),
        end_date=date(2025, 3, 18)
    )
    db.add_all([reservation_1, reservation_2])
    await db.flush()

    await db.commit()
    print("Database seeded successfully!")