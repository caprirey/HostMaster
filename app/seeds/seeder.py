import csv
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.sqlalchemy_models import (
    Country, State, City, Accommodation, RoomType, Room, UserTable, Reservation, Image
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
        email="admin@hotelescolombia.com",
        full_name="Carlos Andrés Gómez",
        hashed_password=get_password_hash("admin123"),
        disabled=False,
        role="admin"
    )
    user1 = UserTable(
        username="maria",
        email="maria.lopez@hotelescolombia.com",
        full_name="María Fernanda López",
        hashed_password=get_password_hash("maria2023"),
        disabled=False,
        role="user"
    )
    db.add_all([admin_user, user1])
    await db.flush()

    # País
    colombia = Country(name="Colombia")
    db.add(colombia)
    await db.flush()

    # Cargar departamentos y municipios desde CSV al lado de seeder.py
    csv_path = Path(__file__).parent / "colombia_departamentos_municipios.csv"
    if not csv_path.exists():
        print(f"CSV file not found at {csv_path}, skipping departments and cities...")
        return

    departments = {}
    cities = []

    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        # Verificar columnas esperadas
        expected_columns = {"REGION", "CÓDIGO DANE DEL DEPARTAMENTO", "DEPARTAMENTO", "CÓDIGO DANE DEL MUNICIPIO", "MUNICIPIO"}
        if not expected_columns.issubset(reader.fieldnames):
            print("CSV does not have the expected columns, skipping...")
            return

        for row in reader:
            dept_code = row["CÓDIGO DANE DEL DEPARTAMENTO"]
            dept_name = row["DEPARTAMENTO"]
            city_name = row["MUNICIPIO"]

            # Agregar departamento si no existe
            if dept_code not in departments:
                dept = State(name=dept_name, country_id=colombia.id)
                departments[dept_code] = dept
                db.add(dept)

        # Flush departamentos para obtener sus IDs
        await db.flush()

        # Mapear códigos DANE a IDs generados
        dept_id_map = {code: dept.id for code, dept in departments.items()}

        # Rebobinar el archivo para leer municipios
        csvfile.seek(0)
        next(reader)  # Saltar encabezado
        for row in reader:
            dept_code = row["CÓDIGO DANE DEL DEPARTAMENTO"]
            city_name = row["MUNICIPIO"]
            city = City(name=city_name, state_id=dept_id_map[dept_code])
            cities.append(city)

    # Insertar ciudades en lote
    db.add_all(cities)
    await db.flush()

    # Alojamientos
    medellin_id = [c.id for c in cities if c.name == "Medellín"][0]
    bogota_id = [c.id for c in cities if c.name == "Bogotá D.C."][0]
    hotel_poblado = Accommodation(name="Hotel El Poblado Plaza", city_id=medellin_id, created_by="admin")
    hotel_tequendama = Accommodation(name="Hotel Tequendama", city_id=bogota_id, created_by="maria")
    db.add_all([hotel_poblado, hotel_tequendama])
    await db.flush()

    # Tipos de habitación
    sencilla = RoomType(name="Habitación Sencilla")
    doble = RoomType(name="Habitación Doble")
    db.add_all([sencilla, doble])
    await db.flush()

    # Habitaciones
    room_101 = Room(accommodation_id=hotel_poblado.id, type_id=sencilla.id, number="101")
    room_201 = Room(accommodation_id=hotel_tequendama.id, type_id=doble.id, number="201")
    db.add_all([room_101, room_201])
    await db.flush()

    # Reservas
    reservation_1 = Reservation(
        user_username="admin",
        room_id=room_101.id,
        start_date=date(2025, 4, 10),
        end_date=date(2025, 4, 15)
    )
    reservation_2 = Reservation(
        user_username="maria",
        room_id=room_201.id,
        start_date=date(2025, 5, 1),
        end_date=date(2025, 5, 5)
    )
    db.add_all([reservation_1, reservation_2])
    await db.flush()

    # Imágenes
    image_1 = Image(url="http://hotelescolombia.com/images/poblado_plaza.jpg", accommodation_id=hotel_poblado.id)
    image_2 = Image(url="http://hotelescolombia.com/images/room_101.jpg", room_id=room_101.id)
    db.add_all([image_1, image_2])
    await db.flush()

    await db.commit()
    print("Database seeded successfully with all Colombian departments and municipalities!")