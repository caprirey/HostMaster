import csv
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.sqlalchemy_models import (
    Country, State, City, Accommodation, RoomType, Room, UserTable, Reservation,
    Image, Review, ExtraService, reservation_extra_service, RoomInventory
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
    hotel_poblado = Accommodation(
        name="Hotel El Poblado Plaza",
        city_id=medellin_id,
        created_by="admin",
        address="Calle 10 # 43-15",
        information="Hotel de lujo en el corazón de El Poblado"
    )
    hotel_tequendama = Accommodation(
        name="Hotel Tequendama",
        city_id=bogota_id,
        created_by="maria",
        address="Carrera 10 # 26-21",
        information="Hotel histórico en el centro de Bogotá"
    )
    db.add_all([hotel_poblado, hotel_tequendama])
    await db.flush()

    # Tipos de habitación
    sencilla = RoomType(name="Habitación Sencilla", max_guests=1, description="habitacion con cama sencilla")
    doble = RoomType(name="Habitación Doble", max_guests=2,description="habitacion con cama doble")
    familiar = RoomType(name="Habitación Familiar", max_guests=4,description="habitacion con dos camas dobles")
    db.add_all([sencilla, doble, familiar])
    await db.flush()

    # Habitaciones
    room_101 = Room(accommodation_id=hotel_poblado.id, type_id=sencilla.id, number="101", price=60000)
    room_201 = Room(accommodation_id=hotel_tequendama.id, type_id=doble.id, number="201", price=60000)
    db.add_all([room_101, room_201])
    await db.flush()

    # Reservas con nuevos campos
    reservation_1 = Reservation(
        user_username="admin",
        room_id=room_101.id,
        accommodation_id=hotel_poblado.id,  # Nuevo campo
        start_date=date(2025, 4, 10),
        end_date=date(2025, 4, 15),
        guest_count=1,
        status="confirmed",  # Nuevo campo
        observations="Reserva confirmada para evento corporativo"  # Nuevo campo
    )
    reservation_2 = Reservation(
        user_username="maria",
        room_id=room_201.id,
        accommodation_id=hotel_tequendama.id,  # Nuevo campo
        start_date=date(2025, 5, 1),
        end_date=date(2025, 5, 5),
        guest_count=1,
        status="pending",  # Nuevo campo
        observations="Esperando pago"  # Nuevo campo
    )
    db.add_all([reservation_1, reservation_2])
    await db.flush()

    # Imágenes
    image_1 = Image(url="static/images/hotel_poblado.jpg", accommodation_id=hotel_poblado.id)
    image_2 = Image(url="static/images/room_101.jpg", room_id=room_101.id)
    db.add_all([image_1, image_2])
    await db.flush()

    # Reseñas (Reviews)
    review_1 = Review(
        accommodation_id=hotel_poblado.id,
        user_username="admin",
        rating=5,
        comment="Excelente servicio y ubicación"
    )
    review_2 = Review(
        accommodation_id=hotel_tequendama.id,
        user_username="maria",
        rating=4,
        comment="Buen hotel, pero el wifi podría mejorar"
    )
    db.add_all([review_1, review_2])
    await db.flush()

    # Servicios Extra (ExtraService)
    breakfast = ExtraService(name="Desayuno", description="Desayuno continental", price=15000)
    parking = ExtraService(name="Parqueadero", description="Estacionamiento privado", price=20000)
    db.add_all([breakfast, parking])
    await db.flush()

    # Relación Reservation-ExtraService (reservation_extra_service)
    reservation_extra_1 = reservation_extra_service.insert().values(
        reservation_id=reservation_1.id,
        extra_service_id=breakfast.id
    )
    reservation_extra_2 = reservation_extra_service.insert().values(
        reservation_id=reservation_2.id,
        extra_service_id=parking.id
    )
    await db.execute(reservation_extra_1)
    await db.execute(reservation_extra_2)
    await db.flush()

    # Inventario de Habitaciones (RoomInventory)
    inventory_1 = RoomInventory(
        room_id=room_101.id,
        product_name="Toallas",
        quantity=10,
        min_quantity=5,
        needs_restock=False
    )
    inventory_2 = RoomInventory(
        room_id=room_201.id,
        product_name="Sábanas",
        quantity=8,
        min_quantity=10,
        needs_restock=True
    )
    db.add_all([inventory_1, inventory_2])
    await db.flush()

    await db.commit()
    print("Database seeded successfully with all Colombian departments, municipalities, and additional data!")