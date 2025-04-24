import csv
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import insert
from app.models.sqlalchemy_models import (
    Country, State, City, Accommodation, RoomType, Room, UserTable, Reservation,
    Image, Review, ExtraService, reservation_extra_service, RoomInventory, Product, room_product
)
from app.utils.auth import get_password_hash
from datetime import date, timedelta

async def seed_database(db: AsyncSession):
    result = await db.execute(select(UserTable))
    if result.scalars().first():
        print("Database already seeded, skipping...")
        return

    # Usuarios
    admin_user = UserTable(
        username="admin",
        email="admin@hostmastercolombia.com",
        full_name="Carlos Andrés Gómez",
        hashed_password=get_password_hash("admin123"),
        disabled=False,
        role="admin"
    )
    user1 = UserTable(
        username="maria",
        email="maria.lopez@hostmastercolombia.com",
        full_name="María Fernanda López",
        hashed_password=get_password_hash("maria2023"),
        disabled=False,
        role="user"
    )
    employee = UserTable(
        username="camilo",
        email="camilo@hostmastercolombia.com",
        full_name="Camilo Prieto",
        hashed_password=get_password_hash("camilo"),
        disabled=False,
        role="employee"
    )
    db.add_all([admin_user, user1, employee])
    await db.flush()

    # País
    colombia = Country(name="Colombia")
    db.add(colombia)
    await db.flush()

    # Cargar departamentos y municipios desde CSV
    csv_path = Path(__file__).parent / "colombia_departamentos_municipios.csv"
    if not csv_path.exists():
        print(f"CSV file not found at {csv_path}, skipping departments and cities...")
        return

    departments = {}
    cities = []

    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        expected_columns = {"REGION", "CÓDIGO DANE DEL DEPARTAMENTO", "DEPARTAMENTO", "CÓDIGO DANE DEL MUNICIPIO", "MUNICIPIO"}
        if not expected_columns.issubset(reader.fieldnames):
            print("CSV does not have the expected columns, skipping...")
            return

        for row in reader:
            dept_code = row["CÓDIGO DANE DEL DEPARTAMENTO"]
            dept_name = row["DEPARTAMENTO"]
            city_name = row["MUNICIPIO"]

            if dept_code not in departments:
                dept = State(name=dept_name, country_id=colombia.id)
                departments[dept_code] = dept
                db.add(dept)

        await db.flush()

        dept_id_map = {code: dept.id for code, dept in departments.items()}

        csvfile.seek(0)
        next(reader)
        for row in reader:
            dept_code = row["CÓDIGO DANE DEL DEPARTAMENTO"]
            city_name = row["MUNICIPIO"]
            city = City(name=city_name, state_id=dept_id_map[dept_code])
            cities.append(city)

    db.add_all(cities)
    await db.flush()

    # Alojamientos
    medellin_id = [c.id for c in cities if c.name == "Medellín"][0]
    bogota_id = [c.id for c in cities if c.name == "Bogotá D.C."][0]
    cartagena_id = [c.id for c in cities if c.name == "Cartagena"][0]
    cali_id = [c.id for c in cities if c.name == "Cali"][0]

    hotel_poblado = Accommodation(
        name="Hotel El Poblado Plaza",
        city_id=medellin_id,
        address="Calle 10 # 43-15",
        information="Hotel de lujo en el corazón de El Poblado"
    )
    hotel_tequendama = Accommodation(
        name="Hotel Tequendama",
        city_id=bogota_id,
        address="Carrera 10 # 26-21",
        information="Hotel histórico en el centro de Bogotá"
    )
    # Nuevos alojamientos
    hotel_casa_luz = Accommodation(
        name="Casa de la Luz",
        city_id=cartagena_id,
        address="Calle del Arsenal # 8-29",
        information="Hotel boutique con vistas al mar en Cartagena"
    )
    hotel_verde_valle = Accommodation(
        name="Verde Valle",
        city_id=cali_id,
        address="Carrera 24 # 5-50",
        information="Hotel ecológico en el corazón de Cali"
    )
    hotel_jardin_secreto = Accommodation(
        name="Jardín Secreto",
        city_id=medellin_id,
        address="Carrera 35 # 7-30",
        information="Hotel tranquilo con jardines en Medellín"
    )
    hotel_cielo_abierto = Accommodation(
        name="Cielo Abierto",
        city_id=bogota_id,
        address="Avenida 19 # 114-65",
        information="Hotel moderno con vistas panorámicas en Bogotá"
    )
    db.add_all([hotel_poblado, hotel_tequendama, hotel_casa_luz, hotel_verde_valle, hotel_jardin_secreto, hotel_cielo_abierto])
    await db.flush()

    # Asociar usuarios a alojamientos mediante la tabla intermedia
    await db.execute(
        insert(Accommodation.__table__.metadata.tables['user_accommodation']),
        [
            {"user_username": "admin", "accommodation_id": hotel_poblado.id},
            {"user_username": "maria", "accommodation_id": hotel_tequendama.id},
            {"user_username": "camilo", "accommodation_id": hotel_poblado.id},
            {"user_username": "admin", "accommodation_id": hotel_casa_luz.id},
            {"user_username": "maria", "accommodation_id": hotel_verde_valle.id},
            {"user_username": "camilo", "accommodation_id": hotel_jardin_secreto.id},
            {"user_username": "admin", "accommodation_id": hotel_cielo_abierto.id}
        ]
    )
    await db.flush()

    # Tipos de habitación
    sencilla = RoomType(name="Habitación Sencilla", max_guests=1, description="Habitación con cama sencilla")
    doble = RoomType(name="Habitación Doble", max_guests=2, description="Habitación con cama doble")
    familiar = RoomType(name="Habitación Familiar", max_guests=4, description="Habitación con dos camas dobles")
    db.add_all([sencilla, doble, familiar])
    await db.flush()

    # Habitaciones
    rooms = []
    # Habitaciones para Hotel El Poblado Plaza
    for i in range(1, 11):
        room_type_id = sencilla.id if i <= 4 else (doble.id if i <= 7 else familiar.id)
        price = 60000 if i <= 4 else (80000 if i <= 7 else 120000)
        rooms.append(Room(
            accommodation_id=hotel_poblado.id,
            type_id=room_type_id,
            number=f"{100 + i}",
            price=price
        ))
    # Habitaciones para Hotel Tequendama
    for i in range(1, 11):
        room_type_id = sencilla.id if i <= 4 else (doble.id if i <= 7 else familiar.id)
        price = 65000 if i <= 4 else (85000 if i <= 7 else 130000)
        rooms.append(Room(
            accommodation_id=hotel_tequendama.id,
            type_id=room_type_id,
            number=f"{200 + i}",
            price=price
        ))
    # Habitaciones para Casa de la Luz
    for i in range(1, 11):
        room_type_id = sencilla.id if i <= 4 else (doble.id if i <= 7 else familiar.id)
        price = 70000 if i <= 4 else (90000 if i <= 7 else 140000)
        rooms.append(Room(
            accommodation_id=hotel_casa_luz.id,
            type_id=room_type_id,
            number=f"{300 + i}",
            price=price
        ))
    # Habitaciones para Verde Valle
    for i in range(1, 11):
        room_type_id = sencilla.id if i <= 4 else (doble.id if i <= 7 else familiar.id)
        price = 62000 if i <= 4 else (82000 if i <= 7 else 125000)
        rooms.append(Room(
            accommodation_id=hotel_verde_valle.id,
            type_id=room_type_id,
            number=f"{400 + i}",
            price=price
        ))
    # Habitaciones para Jardín Secreto
    for i in range(1, 11):
        room_type_id = sencilla.id if i <= 4 else (doble.id if i <= 7 else familiar.id)
        price = 68000 if i <= 4 else (88000 if i <= 7 else 135000)
        rooms.append(Room(
            accommodation_id=hotel_jardin_secreto.id,
            type_id=room_type_id,
            number=f"{500 + i}",
            price=price
        ))
    # Habitaciones para Cielo Abierto
    for i in range(1, 11):
        room_type_id = sencilla.id if i <= 4 else (doble.id if i <= 7 else familiar.id)
        price = 67000 if i <= 4 else (87000 if i <= 7 else 132000)
        rooms.append(Room(
            accommodation_id=hotel_cielo_abierto.id,
            type_id=room_type_id,
            number=f"{600 + i}",
            price=price
        ))
    db.add_all(rooms)
    await db.flush()

    # Reservas (10 por alojamiento)
    reservations = []
    base_date = date(2025, 5, 1)
    users = ["admin", "maria", "camilo"]
    statuses = ["confirmed", "pending", "cancelled"]
    accommodations = [hotel_poblado, hotel_tequendama, hotel_casa_luz, hotel_verde_valle, hotel_jardin_secreto, hotel_cielo_abierto]

    for accom in accommodations:
        # Filtrar las habitaciones de este alojamiento
        accom_rooms = [r for r in rooms if r.accommodation_id == accom.id]
        for i in range(10):
            # Rotar entre las primeras 10 habitaciones del alojamiento
            room = accom_rooms[i % len(accom_rooms)]
            start_date = base_date + timedelta(days=i * 7)
            end_date = start_date + timedelta(days=3)
            user_index = i % 3
            status_index = i % 3
            guest_count = 1 if room.type_id == sencilla.id else (2 if room.type_id == doble.id else 4)
            reservations.append(Reservation(
                user_username=users[user_index],
                room_id=room.id,
                accommodation_id=accom.id,
                start_date=start_date,
                end_date=end_date,
                guest_count=guest_count,
                status=statuses[status_index],
                observations=f"Reserva {i + 1} para habitación {room.number} en {accom.name}"
            ))
    db.add_all(reservations)
    await db.flush()

    # Imágenes
    image_1 = Image(url="static/images/hotel_poblado.jpg", accommodation_id=hotel_poblado.id)
    image_2 = Image(url="static/images/room_101.jpg", room_id=rooms[0].id)
    image_3 = Image(url="static/images/hotel_tequendama.jpg", accommodation_id=hotel_tequendama.id)
    image_4 = Image(url="static/images/hotel_casa_luz.jpg", accommodation_id=hotel_casa_luz.id)
    image_5 = Image(url="static/images/hotel_verde_valle.jpg", accommodation_id=hotel_verde_valle.id)
    image_6 = Image(url="static/images/hotel_jardin_secreto.jpg", accommodation_id=hotel_jardin_secreto.id)
    image_7 = Image(url="static/images/hotel_cielo_abierto.jpg", accommodation_id=hotel_cielo_abierto.id)
    db.add_all([image_1, image_2, image_3, image_4, image_5, image_6, image_7])
    await db.flush()

    # Reseñas
    reviews = [
        Review(
            accommodation_id=hotel_poblado.id,
            user_username="admin",
            rating=5,
            comment="Excelente servicio y ubicación"
        ),
        Review(
            accommodation_id=hotel_tequendama.id,
            user_username="maria",
            rating=4,
            comment="Buen hotel, pero el wifi podría mejorar"
        ),
        Review(
            accommodation_id=hotel_casa_luz.id,
            user_username="camilo",
            rating=5,
            comment="Vista espectacular y atención impecable"
        ),
        Review(
            accommodation_id=hotel_verde_valle.id,
            user_username="admin",
            rating=4,
            comment="Ambiente relajante, ideal para descansar"
        ),
        Review(
            accommodation_id=hotel_jardin_secreto.id,
            user_username="maria",
            rating=5,
            comment="Los jardines son un sueño"
        ),
        Review(
            accommodation_id=hotel_cielo_abierto.id,
            user_username="camilo",
            rating=4,
            comment="Moderno y cómodo, pero algo ruidoso"
        )
    ]
    db.add_all(reviews)
    await db.flush()

    # Servicios Extra
    breakfast = ExtraService(name="Desayuno", description="Desayuno continental", price=15000)
    parking = ExtraService(name="Parqueadero", description="Estacionamiento privado", price=20000)
    db.add_all([breakfast, parking])
    await db.flush()

    # Relación Reservation-ExtraService
    reservation_extra_1 = reservation_extra_service.insert().values(
        reservation_id=reservations[0].id,
        extra_service_id=breakfast.id
    )
    reservation_extra_2 = reservation_extra_service.insert().values(
        reservation_id=reservations[1].id,
        extra_service_id=parking.id
    )
    await db.execute(reservation_extra_1)
    await db.execute(reservation_extra_2)
    await db.flush()

    # Inventario de Habitaciones
    inventory_items = []
    for room in rooms:
        inventory_items.append(RoomInventory(
            room_id=room.id,
            product_name="Toallas",
            quantity=10,
            min_quantity=5,
            needs_restock=False
        ))
        inventory_items.append(RoomInventory(
            room_id=room.id,
            product_name="Sábanas",
            quantity=8,
            min_quantity=10,
            needs_restock=True
        ))
    db.add_all(inventory_items)
    await db.flush()

    # Productos
    towels = Product(
        name="Toallas",
        description="Toallas blancas de algodón",
        price=5.0
    )
    sheets = Product(
        name="Sábanas",
        description="Sábanas de algodón 200 hilos",
        price=10.0
    )
    pillows = Product(
        name="Almohadas",
        description="Almohadas de plumas",
        price=15.0
    )
    db.add_all([towels, sheets, pillows])
    await db.flush()

    # Relación Room-Product
    room_product_entries = []
    for room in rooms:
        room_product_entries.append(room_product.insert().values(
            room_id=room.id,
            product_id=towels.id,
            quantity=5,
            needs_restock=False
        ))
        room_product_entries.append(room_product.insert().values(
            room_id=room.id,
            product_id=sheets.id,
            quantity=2,
            needs_restock=True
        ))
        if room.type_id == familiar.id:  # Habitaciones familiares también tienen almohadas
            room_product_entries.append(room_product.insert().values(
                room_id=room.id,
                product_id=pillows.id,
                quantity=4,
                needs_restock=False
            ))
    for entry in room_product_entries:
        await db.execute(entry)
    await db.flush()

    await db.commit()
    print("Database seeded successfully with all Colombian departments, municipalities, additional accommodations, rooms, reservations, and products!")