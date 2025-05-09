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
from datetime import date, timedelta, datetime

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
        firstname="Carlos",
        lastname="Gómez",
        document_number="1234567890",
        hashed_password=get_password_hash("admin123"),
        disabled=False,
        role="admin",
        image="static/images/admin.jpg"
    )
    user1 = UserTable(
        username="maria",
        email="maria.lopez@hotelescolombia.com",
        full_name="María Fernanda López",
        firstname="María",
        lastname="López",
        document_number="9876543210",
        hashed_password=get_password_hash("maria"),
        disabled=False,
        role="client",
        image="static/images/maria.jpg"
    )
    employee = UserTable(
        username="camilo",
        email="camilo@hotelescolombia.com",
        full_name="Camilo Prieto",
        firstname="Camilo",
        lastname="Prieto",
        document_number="4567891230",
        hashed_password=get_password_hash("camilo"),
        disabled=False,
        role="employee",
        image="static/images/camilo.jpg"
    )
    user2 = UserTable(
        username="juan",
        email="juan.perez@hotelescolombia.com",
        full_name="Juan David Pérez",
        firstname="Juan",
        lastname="Pérez",
        document_number="1122334455",
        hashed_password=get_password_hash("juan123"),
        disabled=False,
        role="client",
        image="static/images/juan.jpg"
    )
    user3 = UserTable(
        username="sofia",
        email="sofia.garcia@hotelescolombia.com",
        full_name="Sofía Alejandra García",
        firstname="Sofía",
        lastname="García",
        document_number="2233445566",
        hashed_password=get_password_hash("sofia123"),
        disabled=False,
        role="client",
        image="static/images/sofia.jpg"
    )
    user4 = UserTable(
        username="pedro",
        email="pedro.martinez@hotelescolombia.com",
        full_name="Pedro Antonio Martínez",
        firstname="Pedro",
        lastname="Martínez",
        document_number="3344556677",
        hashed_password=get_password_hash("pedro123"),
        disabled=False,
        role="client",
        image="static/images/pedro.jpg"
    )
    user5 = UserTable(
        username="laura",
        email="laura.rodriguez@hotelescolombia.com",
        full_name="Laura Valentina Rodríguez",
        firstname="Laura",
        lastname="Rodríguez",
        document_number="4455667788",
        hashed_password=get_password_hash("laura123"),
        disabled=False,
        role="client",
        image="static/images/laura.jpg"
    )
    db.add_all([admin_user, user1, employee, user2, user3, user4, user5])
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

    # Asociar usuarios a alojamientos
    await db.execute(
        insert(Accommodation.__table__.metadata.tables['user_accommodation']),
        [
            {"user_username": "admin", "accommodation_id": hotel_poblado.id},
            {"user_username": "maria", "accommodation_id": hotel_tequendama.id},
            {"user_username": "camilo", "accommodation_id": hotel_poblado.id},
            {"user_username": "admin", "accommodation_id": hotel_casa_luz.id},
            {"user_username": "maria", "accommodation_id": hotel_verde_valle.id},
            {"user_username": "camilo", "accommodation_id": hotel_jardin_secreto.id},
            {"user_username": "admin", "accommodation_id": hotel_cielo_abierto.id},
            {"user_username": "juan", "accommodation_id": hotel_poblado.id},
            {"user_username": "sofia", "accommodation_id": hotel_tequendama.id},
            {"user_username": "pedro", "accommodation_id": hotel_casa_luz.id},
            {"user_username": "laura", "accommodation_id": hotel_verde_valle.id},
            {"user_username": "juan", "accommodation_id": hotel_jardin_secreto.id},
            {"user_username": "sofia", "accommodation_id": hotel_cielo_abierto.id}
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
    for i in range(1, 11):
        room_type_id = sencilla.id if i <= 4 else (doble.id if i <= 7 else familiar.id)
        price = 60000 if i <= 4 else (80000 if i <= 7 else 120000)
        rooms.append(Room(
            accommodation_id=hotel_poblado.id,
            type_id=room_type_id,
            number=f"{100 + i}",
            price=price,
            isAvailable=True
        ))
    for i in range(1, 11):
        room_type_id = sencilla.id if i <= 4 else (doble.id if i <= 7 else familiar.id)
        price = 65000 if i <= 4 else (85000 if i <= 7 else 130000)
        rooms.append(Room(
            accommodation_id=hotel_tequendama.id,
            type_id=room_type_id,
            number=f"{200 + i}",
            price=price,
            isAvailable=True
        ))
    for i in range(1, 11):
        room_type_id = sencilla.id if i <= 4 else (doble.id if i <= 7 else familiar.id)
        price = 70000 if i <= 4 else (90000 if i <= 7 else 140000)
        rooms.append(Room(
            accommodation_id=hotel_casa_luz.id,
            type_id=room_type_id,
            number=f"{300 + i}",
            price=price,
            isAvailable=True
        ))
    for i in range(1, 11):
        room_type_id = sencilla.id if i <= 4 else (doble.id if i <= 7 else familiar.id)
        price = 62000 if i <= 4 else (82000 if i <= 7 else 125000)
        rooms.append(Room(
            accommodation_id=hotel_verde_valle.id,
            type_id=room_type_id,
            number=f"{400 + i}",
            price=price,
            isAvailable=True
        ))
    for i in range(1, 11):
        room_type_id = sencilla.id if i <= 4 else (doble.id if i <= 7 else familiar.id)
        price = 68000 if i <= 4 else (88000 if i <= 7 else 135000)
        rooms.append(Room(
            accommodation_id=hotel_jardin_secreto.id,
            type_id=room_type_id,
            number=f"{500 + i}",
            price=price,
            isAvailable=True
        ))
    for i in range(1, 11):
        room_type_id = sencilla.id if i <= 4 else (doble.id if i <= 7 else familiar.id)
        price = 67000 if i <= 4 else (87000 if i <= 7 else 132000)
        rooms.append(Room(
            accommodation_id=hotel_cielo_abierto.id,
            type_id=room_type_id,
            number=f"{600 + i}",
            price=price,
            isAvailable=True
        ))
    db.add_all(rooms)
    await db.flush()

    # Reservas
    reservations = []
    base_date = date(2025, 5, 1)
    client_usernames = ["maria", "juan", "sofia", "pedro", "laura"]
    statuses = ["confirmed", "pending", "cancelled"]
    accommodations = [hotel_poblado, hotel_tequendama, hotel_casa_luz, hotel_verde_valle, hotel_jardin_secreto, hotel_cielo_abierto]

    for accom in accommodations:
        accom_rooms = [r for r in rooms if r.accommodation_id == accom.id]
        for i in range(10):
            room = accom_rooms[i % len(accom_rooms)]
            start_date = base_date + timedelta(days=i * 7)
            end_date = start_date + timedelta(days=3)
            client_index = (i % 5)
            status_index = i % 3
            guest_count = 1 if room.type_id == sencilla.id else (2 if room.type_id == doble.id else 4)
            reservations.append(Reservation(
                user_username=client_usernames[client_index],
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
            comment="Excelente servicio y ubicación",
            created_at=datetime.utcnow()
        ),
        Review(
            accommodation_id=hotel_tequendama.id,
            user_username="maria",
            rating=4,
            comment="Buen hotel, pero el wifi podría mejorar",
            created_at=datetime.utcnow()
        ),
        Review(
            accommodation_id=hotel_casa_luz.id,
            user_username="camilo",
            rating=5,
            comment="Vista espectacular y atención impecable",
            created_at=datetime.utcnow()
        ),
        Review(
            accommodation_id=hotel_verde_valle.id,
            user_username="admin",
            rating=4,
            comment="Ambiente relajante, ideal para descansar",
            created_at=datetime.utcnow()
        ),
        Review(
            accommodation_id=hotel_jardin_secreto.id,
            user_username="maria",
            rating=5,
            comment="Los jardines son un sueño",
            created_at=datetime.utcnow()
        ),
        Review(
            accommodation_id=hotel_cielo_abierto.id,
            user_username="camilo",
            rating=4,
            comment="Moderno y cómodo, pero algo ruidoso",
            created_at=datetime.utcnow()
        )
    ]
    db.add_all(reviews)
    await db.flush()

    # Servicios Extra
    breakfast = ExtraService(
        name="Desayuno",
        description="Desayuno continental",
        price=15000
    )
    parking = ExtraService(
        name="Parqueadero",
        description="Estacionamiento privado",
        price=20000
    )
    wifi = ExtraService(
        name="WiFi Premium",
        description="Internet de alta velocidad",
        price=10000
    )
    spa = ExtraService(
        name="Spa",
        description="Sesión de spa relajante",
        price=50000
    )
    db.add_all([breakfast, parking, wifi, spa])
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
    reservation_extra_3 = reservation_extra_service.insert().values(
        reservation_id=reservations[2].id,
        extra_service_id=wifi.id
    )
    reservation_extra_4 = reservation_extra_service.insert().values(
        reservation_id=reservations[3].id,
        extra_service_id=spa.id
    )
    await db.execute(reservation_extra_1)
    await db.execute(reservation_extra_2)
    await db.execute(reservation_extra_3)
    await db.execute(reservation_extra_4)
    await db.flush()

    # Productos
    tv_32 = Product(
        name="TV LED 32 pulgadas",
        description="Televisor LED Full HD de 32 pulgadas",
        price=1200000.0
    )
    tv_40 = Product(
        name="TV LED 40 pulgadas",
        description="Televisor LED Full HD de 40 pulgadas",
        price=1800000.0
    )
    tv_50 = Product(
        name="TV LED 50 pulgadas",
        description="Televisor LED 4K de 50 pulgadas",
        price=2500000.0
    )
    bed_single = Product(
        name="Cama Sencilla",
        description="Cama sencilla de madera con acabado moderno",
        price=800000.0
    )
    bed_double = Product(
        name="Cama Doble",
        description="Cama doble de madera con acabado moderno",
        price=1500000.0
    )
    mattress_single = Product(
        name="Colchón Sencillo",
        description="Colchón ortopédico sencillo de alta densidad",
        price=500000.0
    )
    mattress_double = Product(
        name="Colchón Doble",
        description="Colchón ortopédico doble de alta densidad",
        price=900000.0
    )
    nightstand = Product(
        name="Nochero",
        description="Mesa de noche de madera con un cajón",
        price=200000.0
    )
    lamp = Product(
        name="Lámpara",
        description="Lámpara de mesa con diseño moderno",
        price=100000.0
    )
    hairdryer = Product(
        name="Secador de Pelo",
        description="Secador de pelo de 1800W",
        price=150000.0
    )
    db.add_all([tv_32, tv_40, tv_50, bed_single, bed_double, mattress_single, mattress_double, nightstand, lamp, hairdryer])
    await db.flush()

    # Inventario de Habitaciones
    inventory_items = []
    room_product_entries = []
    for room in rooms:
        is_single = room.type_id == sencilla.id
        is_double = room.type_id == doble.id
        is_family = room.type_id == familiar.id

        inventory_items.extend([
            RoomInventory(
                room_id=room.id,
                product_name="Secador de Pelo",
                quantity=1,
                min_quantity=1,
                needs_restock=False
            ),
            RoomInventory(
                room_id=room.id,
                product_name="Lámpara",
                quantity=1 if is_single else 2,
                min_quantity=1 if is_single else 2,
                needs_restock=False
            ),
            RoomInventory(
                room_id=room.id,
                product_name="Nochero",
                quantity=1 if is_single else 2,
                min_quantity=1 if is_single else 2,
                needs_restock=False
            )
        ])

        if is_single:
            inventory_items.extend([
                RoomInventory(
                    room_id=room.id,
                    product_name="TV LED 32 pulgadas",
                    quantity=1,
                    min_quantity=1,
                    needs_restock=False
                ),
                RoomInventory(
                    room_id=room.id,
                    product_name="Cama Sencilla",
                    quantity=1,
                    min_quantity=1,
                    needs_restock=False
                ),
                RoomInventory(
                    room_id=room.id,
                    product_name="Colchón Sencillo",
                    quantity=1,
                    min_quantity=1,
                    needs_restock=False
                )
            ])
        elif is_double:
            inventory_items.extend([
                RoomInventory(
                    room_id=room.id,
                    product_name="TV LED 40 pulgadas",
                    quantity=1,
                    min_quantity=1,
                    needs_restock=False
                ),
                RoomInventory(
                    room_id=room.id,
                    product_name="Cama Doble",
                    quantity=1,
                    min_quantity=1,
                    needs_restock=False
                ),
                RoomInventory(
                    room_id=room.id,
                    product_name="Colchón Doble",
                    quantity=1,
                    min_quantity=1,
                    needs_restock=False
                )
            ])
        elif is_family:
            inventory_items.extend([
                RoomInventory(
                    room_id=room.id,
                    product_name="TV LED 50 pulgadas",
                    quantity=1,
                    min_quantity=1,
                    needs_restock=False
                ),
                RoomInventory(
                    room_id=room.id,
                    product_name="Cama Doble",
                    quantity=2,
                    min_quantity=2,
                    needs_restock=False
                ),
                RoomInventory(
                    room_id=room.id,
                    product_name="Colchón Doble",
                    quantity=2,
                    min_quantity=2,
                    needs_restock=False
                )
            ])

        room_product_entries.extend([
            room_product.insert().values(
                room_id=room.id,
                product_id=hairdryer.id,
                quantity=1,
                needs_restock=False
            ),
            room_product.insert().values(
                room_id=room.id,
                product_id=lamp.id,
                quantity=1 if is_single else 2,
                needs_restock=False
            ),
            room_product.insert().values(
                room_id=room.id,
                product_id=nightstand.id,
                quantity=1 if is_single else 2,
                needs_restock=False
            )
        ])

        if is_single:
            room_product_entries.extend([
                room_product.insert().values(
                    room_id=room.id,
                    product_id=tv_32.id,
                    quantity=1,
                    needs_restock=False
                ),
                room_product.insert().values(
                    room_id=room.id,
                    product_id=bed_single.id,
                    quantity=1,
                    needs_restock=False
                ),
                room_product.insert().values(
                    room_id=room.id,
                    product_id=mattress_single.id,
                    quantity=1,
                    needs_restock=False
                )
            ])
        elif is_double:
            room_product_entries.extend([
                room_product.insert().values(
                    room_id=room.id,
                    product_id=tv_40.id,
                    quantity=1,
                    needs_restock=False
                ),
                room_product.insert().values(
                    room_id=room.id,
                    product_id=bed_double.id,
                    quantity=1,
                    needs_restock=False
                ),
                room_product.insert().values(
                    room_id=room.id,
                    product_id=mattress_double.id,
                    quantity=1,
                    needs_restock=False
                )
            ])
        elif is_family:
            room_product_entries.extend([
                room_product.insert().values(
                    room_id=room.id,
                    product_id=tv_50.id,
                    quantity=1,
                    needs_restock=False
                ),
                room_product.insert().values(
                    room_id=room.id,
                    product_id=bed_double.id,
                    quantity=2,
                    needs_restock=False
                ),
                room_product.insert().values(
                    room_id=room.id,
                    product_id=mattress_double.id,
                    quantity=2,
                    needs_restock=False
                )
            ])

    db.add_all(inventory_items)
    await db.flush()

    for entry in room_product_entries:
        await db.execute(entry)
    await db.flush()

    await db.commit()
    print("Database seeded successfully with all Colombian departments, municipalities, accommodations, rooms, reservations, and fixed inventory items!")