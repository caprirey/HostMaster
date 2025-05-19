import csv
import os
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import insert
from app.models.sqlalchemy_models import (
    Country, State, City, Accommodation, RoomType, Room, UserTable, Reservation,
    Image, Review, ExtraService, reservation_extra_service, RoomInventory, Product, room_product,
    Maintenance, MaintenanceStatus, MaintenancePriority
)
from app.utils.auth import get_password_hash
from app.config.settings import STATIC_DIR, IMAGES_DIR
from datetime import date, timedelta, datetime
from random import randint, shuffle, sample

async def seed_database(db: AsyncSession):
    result = await db.execute(select(UserTable))
    if result.scalars().first():
        print("Database already seeded, skipping...")
        return

    # Usuarios
    admin_user = UserTable(
        username="admin",
        email="admin@yopmail.com",
        full_name="Carlos Andrés Gómez",
        firstname="Carlos",
        lastname="Gómez",
        document_number="1234567890",
        hashed_password=get_password_hash("admin123"),
        disabled=False,
        role="admin",
        image=f"/{os.path.join(STATIC_DIR, 'users', 'user_admin.png').replace(os.sep, '/')}",
        phone_number="+573183894217"
    )
    user1 = UserTable(
        username="maria",
        email="maria.lopez@yopmail.com",
        full_name="María Fernanda López",
        firstname="María",
        lastname="López",
        document_number="9876543210",
        hashed_password=get_password_hash("maria"),
        disabled=False,
        role="client",
        image=f"/{os.path.join(STATIC_DIR, 'users', 'user_mujer.jpg').replace(os.sep, '/')}",
        phone_number="+573112512612"
    )
    employee = UserTable(
        username="camilo",
        email="camilo@yopmail.com",
        full_name="Camilo Prieto",
        firstname="Camilo",
        lastname="Prieto",
        document_number="4567891230",
        hashed_password=get_password_hash("camilo"),
        disabled=False,
        role="employee",
        image=f"/{os.path.join(STATIC_DIR, IMAGES_DIR, 'user_hombre.jpg').replace(os.sep, '/')}",
        phone_number="+573044315484"
    )
    user2 = UserTable(
        username="juan",
        email="juan.perez@yopmail.com",
        full_name="Juan David Pérez",
        firstname="Juan",
        lastname="Pérez",
        document_number="1122334455",
        hashed_password=get_password_hash("juan123"),
        disabled=False,
        role="client",
        image=f"/{os.path.join(STATIC_DIR, 'users', 'user_hombre.jpg').replace(os.sep, '/')}",
        phone_number="+573044315484"
    )
    user3 = UserTable(
        username="sofia",
        email="sofia.garcia@yopmail.com",
        full_name="Sofía Alejandra García",
        firstname="Sofía",
        lastname="García",
        document_number="2233445566",
        hashed_password=get_password_hash("sofia123"),
        disabled=False,
        role="client",
        image=f"/{os.path.join(STATIC_DIR, 'users', 'user_mujer.jpg').replace(os.sep, '/')}",
        phone_number="+573044315484"
    )
    user4 = UserTable(
        username="pedro",
        email="pedro.martinez@yopmail.com",
        full_name="Pedro Antonio Martínez",
        firstname="Pedro",
        lastname="Martínez",
        document_number="3344556677",
        hashed_password=get_password_hash("pedro123"),
        disabled=False,
        role="client",
        image=f"/{os.path.join(STATIC_DIR, 'users', 'user_hombre.jpg').replace(os.sep, '/')}",
        phone_number="+573044315484"
    )
    user5 = UserTable(
        username="laura",
        email="laura.rodriguez@yopmail.com",
        full_name="Laura Valentina Rodríguez",
        firstname="Laura",
        lastname="Rodríguez",
        document_number="4455667788",
        hashed_password=get_password_hash("laura123"),
        disabled=False,
        role="client",
        image=f"/{os.path.join(STATIC_DIR, 'users', 'user_mujer.jpg').replace(os.sep, '/')}",
        phone_number="+573044315484"
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
            {"user_username": "camilo", "accommodation_id": hotel_poblado.id},
            {"user_username": "camilo", "accommodation_id": hotel_jardin_secreto.id},
        ]
    )
    await db.flush()

    # Tipos de habitación
    sencilla = RoomType(name="Habitación Sencilla", max_guests=1, description="Habitación con cama sencilla")
    doble = RoomType(name="Habitación Doble", max_guests=2, description="Habitación con cama doble")
    familiar = RoomType(name="Habitación Familiar", max_guests=4, description="Habitación con dos camas dobles")
    db.add_all([sencilla, doble, familiar])
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

    # Habitaciones
    rooms = []

    # Hotel El Poblado Plaza: 30 habitaciones, 3 pisos (8 Sencillas, 12 Dobles, 10 Familiares)
    for floor in range(1, 4):
        for i in range(1, 11):  # 10 habitaciones por piso
            room_num = f"{floor}{i:02d}"  # e.g., 101, 102, ..., 310
            if i <= 3 and floor <= 3:  # Sencillas (8 en total)
                room_type_id = sencilla.id
                price = 80000
            elif i <= 6:  # Dobles (12 en total)
                room_type_id = doble.id
                price = 110000
            else:  # Familiares (10 en total)
                room_type_id = familiar.id
                price = 160000
            rooms.append(Room(
                accommodation_id=hotel_poblado.id,
                type_id=room_type_id,
                number=room_num,
                price=price,
                isAvailable=True
            ))

    # Hotel Tequendama: 30 habitaciones, 3 pisos (7 Sencillas, 13 Dobles, 10 Familiares)
    for floor in range(1, 4):
        for i in range(1, 11):  # 10 habitaciones por piso
            room_num = f"{floor}{i:02d}"
            if i <= 3 and floor <= 3:  # Sencillas (7 en total, omitiendo una)
                room_type_id = sencilla.id if i != 3 or floor != 3 else doble.id
                price = 70000 if room_type_id == sencilla.id else 95000
            elif i <= 6:  # Dobles (13 en total)
                room_type_id = doble.id
                price = 95000
            else:  # Familiares (10 en total)
                room_type_id = familiar.id
                price = 140000
            rooms.append(Room(
                accommodation_id=hotel_tequendama.id,
                type_id=room_type_id,
                number=room_num,
                price=price,
                isAvailable=True
            ))

    # Casa de la Luz: 20 habitaciones, 2 pisos (5 Sencillas, 8 Dobles, 7 Familiares)
    for floor in range(1, 3):
        for i in range(1, 11):  # 10 habitaciones por piso
            room_num = f"{floor}{i:02d}"
            if i <= 3 and floor == 1:  # Sencillas (5 en total)
                room_type_id = sencilla.id
                price = 90000
            elif i <= 6:  # Dobles (8 en total)
                room_type_id = doble.id
                price = 130000
            else:  # Familiares (7 en total)
                room_type_id = familiar.id
                price = 180000
            rooms.append(Room(
                accommodation_id=hotel_casa_luz.id,
                type_id=room_type_id,
                number=room_num,
                price=price,
                isAvailable=True
            ))

    # Verde Valle: 25 habitaciones, 3 pisos (6 Sencillas, 10 Dobles, 9 Familiares)
    for floor in range(1, 4):
        for i in range(1, 9 if floor == 3 else 11):  # 10 habitaciones en pisos 1-2, 5 en piso 3
            room_num = f"{floor}{i:02d}"
            if i <= 3 and floor <= 2:  # Sencillas (6 en total)
                room_type_id = sencilla.id
                price = 75000
            elif i <= 6:  # Dobles (10 en total)
                room_type_id = doble.id
                price = 100000
            else:  # Familiares (9 en total)
                room_type_id = familiar.id
                price = 150000
            rooms.append(Room(
                accommodation_id=hotel_verde_valle.id,
                type_id=room_type_id,
                number=room_num,
                price=price,
                isAvailable=True
            ))

    # Jardín Secreto: 22 habitaciones, 2 pisos (5 Sencillas, 9 Dobles, 8 Familiares)
    for floor in range(1, 3):
        for i in range(1, 12 if floor == 1 else 11):  # 11 habitaciones en piso 1, 11 en piso 2
            room_num = f"{floor}{i:02d}"
            if i <= 3 and floor == 1:  # Sencillas (5 en total)
                room_type_id = sencilla.id
                price = 85000
            elif i <= 6:  # Dobles (9 en total)
                room_type_id = doble.id
                price = 120000
            else:  # Familiares (8 en total)
                room_type_id = familiar.id
                price = 170000
            rooms.append(Room(
                accommodation_id=hotel_jardin_secreto.id,
                type_id=room_type_id,
                number=room_num,
                price=price,
                isAvailable=True
            ))

    # Cielo Abierto: 28 habitaciones, 3 pisos (7 Sencillas, 11 Dobles, 10 Familiares)
    for floor in range(1, 4):
        for i in range(1, 10 if floor == 3 else 11):  # 10 habitaciones en pisos 1-2, 8 en piso 3
            room_num = f"{floor}{i:02d}"
            if i <= 3 and floor <= 3:  # Sencillas (7 en total)
                room_type_id = sencilla.id
                price = 78000
            elif i <= 6:  # Dobles (11 en total)
                room_type_id = doble.id
                price = 105000
            else:  # Familiares (10 en total)
                room_type_id = familiar.id
                price = 155000
            rooms.append(Room(
                accommodation_id=hotel_cielo_abierto.id,
                type_id=room_type_id,
                number=room_num,
                price=price,
                isAvailable=True
            ))

    db.add_all(rooms)
    await db.flush()

    # Reservas y Servicios Extra
    reservations = []
    reservation_extra_entries = []
    client_usernames = ["maria", "juan", "sofia", "pedro", "laura"]
    accommodations = [hotel_poblado, hotel_tequendama, hotel_casa_luz, hotel_verde_valle, hotel_jardin_secreto, hotel_cielo_abierto]
    start_month = date(2025, 5, 1)
    end_month = date(2025, 5, 31)
    max_reservations_per_day = 5  # Máximo de reservas por día por alojamiento
    extra_services = [breakfast, parking, wifi, spa]  # Servicios extra disponibles

    for accom in accommodations:
        accom_rooms = [r for r in rooms if r.accommodation_id == accom.id]
        # Mapa para rastrear ocupación de habitaciones por día
        room_availability = {room.id: [] for room in accom_rooms}

        for day in range((end_month - start_month).days + 1):
            current_date = start_month + timedelta(days=day)
            num_reservations = randint(1, max_reservations_per_day)  # Entre 1 y 5 reservas por día

            # Mezclar habitaciones para asignación aleatoria
            available_rooms = accom_rooms.copy()
            shuffle(available_rooms)

            for _ in range(min(num_reservations, len(available_rooms))):
                # Seleccionar una habitación disponible
                for room in available_rooms:
                    # Verificar si la habitación está libre para las fechas
                    stay_length = randint(1, 7)  # Estadía entre 1 y 7 noches
                    start_date = current_date
                    end_date = start_date + timedelta(days=stay_length)

                    if end_date > end_month:
                        end_date = end_month
                        stay_length = (end_date - start_date).days or 1

                    # Comprobar conflictos
                    conflict = False
                    for reserved_start, reserved_end in room_availability[room.id]:
                        if not (end_date < reserved_start or start_date > reserved_end):
                            conflict = True
                            break

                    if conflict:
                        continue

                    # Habitación disponible, crear reserva
                    guest_count = 1 if room.type_id == sencilla.id else (2 if room.type_id == doble.id else 4)
                    status = "confirmed" if randint(1, 100) <= 90 else "pending"

                    reservation = Reservation(
                        user_username=client_usernames[randint(0, len(client_usernames) - 1)],
                        room_id=room.id,
                        accommodation_id=accom.id,
                        start_date=start_date,
                        end_date=end_date,
                        guest_count=guest_count,
                        status=status,
                        observations=f"Reserva para habitación {room.number} en {accom.name} desde {start_date}"
                    )
                    reservations.append(reservation)

                    # Marcar habitación como ocupada
                    room_availability[room.id].append((start_date, end_date))
                    available_rooms.remove(room)

                    # Asignar servicios extra con 50% de probabilidad
                    if randint(1, 100) <= 50:
                        num_services = randint(1, 2)  # 1 o 2 servicios extra
                        selected_services = sample(extra_services, num_services)
                        for service in selected_services:
                            reservation_extra_entries.append({
                                "reservation_id": None,  # Se actualizará después
                                "extra_service_id": service.id
                            })

                    break  # Pasar a la siguiente reserva

    # Agregar reservas a la base de datos
    db.add_all(reservations)
    await db.flush()

    # Actualizar reservation_id en servicios extra
    for i, entry in enumerate(reservation_extra_entries):
        if i < len(reservations):
            entry["reservation_id"] = reservations[i].id
            await db.execute(
                reservation_extra_service.insert().values(
                    reservation_id=entry["reservation_id"],
                    extra_service_id=entry["extra_service_id"]
                )
            )

    await db.flush()

    # Mantenimientos
    maintenances = [
        Maintenance(
            description="Reparar aire acondicionado",
            status=MaintenanceStatus.PENDING,
            priority=MaintenancePriority.HIGH,
            room_id=[r.id for r in rooms if r.accommodation_id == hotel_poblado.id and r.number == "101"][0],
            accommodation_id=hotel_poblado.id,
            created_by="camilo",
            assigned_to="camilo",
            created_at=date(2025, 5, 17),
            updated_at=date(2025, 5, 17)
        ),
        Maintenance(
            description="Reemplazar bombilla fundida",
            status=MaintenanceStatus.IN_PROGRESS,
            priority=MaintenancePriority.MEDIUM,
            room_id=[r.id for r in rooms if r.accommodation_id == hotel_tequendama.id and r.number == "205"][0],
            accommodation_id=hotel_tequendama.id,
            created_by="admin",
            assigned_to="camilo",
            created_at=date(2025, 5, 15),
            updated_at=date(2025, 5, 17)
        ),
        Maintenance(
            description="Limpiar alfombra manchada",
            status=MaintenanceStatus.PENDING,
            priority=MaintenancePriority.LOW,
            room_id=[r.id for r in rooms if r.accommodation_id == hotel_casa_luz.id and r.number == "108"][0],
            accommodation_id=hotel_casa_luz.id,
            created_by="admin",
            assigned_to="camilo",
            created_at=date(2025, 5, 12),
            updated_at=date(2025, 5, 17)
        ),
    ]
    db.add_all(maintenances)
    await db.flush()

    # Imágenes
    images = []

    # Imágenes para alojamientos
    images.append(Image(url=f"/{os.path.join(STATIC_DIR, IMAGES_DIR, 'hotel_0.jpg').replace(os.sep, '/')}", accommodation_id=hotel_poblado.id))
    images.append(Image(url=f"/{os.path.join(STATIC_DIR, IMAGES_DIR, 'hotel_1.jpg').replace(os.sep, '/')}", accommodation_id=hotel_tequendama.id))
    images.append(Image(url=f"/{os.path.join(STATIC_DIR, IMAGES_DIR, 'hotel_2.jpg').replace(os.sep, '/')}", accommodation_id=hotel_casa_luz.id))
    images.append(Image(url=f"/{os.path.join(STATIC_DIR, IMAGES_DIR, 'hotel_3.jpg').replace(os.sep, '/')}", accommodation_id=hotel_verde_valle.id))
    images.append(Image(url=f"/{os.path.join(STATIC_DIR, IMAGES_DIR, 'hotel_4.jpg').replace(os.sep, '/')}", accommodation_id=hotel_jardin_secreto.id))
    images.append(Image(url=f"/{os.path.join(STATIC_DIR, IMAGES_DIR, 'hotel_5.jpg').replace(os.sep, '/')}", accommodation_id=hotel_cielo_abierto.id))

    # Imágenes para habitaciones
    sencilla_images = [
        "habitacion_sencilla_0.jpg",
        "habitacion_sencilla_1.jpg",
        "habitacion_sencilla_2.jpg",
        "habitacion_sencilla_3.jpg"
    ]
    doble_images = [
        "habitacion_doble_0.jpg",
        "habitacion_doble_1.jpg",
        "habitacion_doble_2.jpg",
        "habitacion_doble_3.jpg"
    ]
    familiar_images = [
        "habitacion_familiar_0.jpg",
        "habitacion_familiar_1.jpg",
        "habitacion_familiar_2.jpg",
        "habitacion_familiar_3.jpg"
    ]

    for accom in accommodations:
        accom_rooms = [r for r in rooms if r.accommodation_id == accom.id]
        sencilla_rooms = [r for r in accom_rooms if r.type_id == sencilla.id]
        doble_rooms = [r for r in accom_rooms if r.type_id == doble.id]
        familiar_rooms = [r for r in accom_rooms if r.type_id == familiar.id]

        for i, room in enumerate(sencilla_rooms):
            image_name = sencilla_images[i % len(sencilla_images)]
            images.append(Image(
                url=f"/{os.path.join(STATIC_DIR, IMAGES_DIR, image_name).replace(os.sep, '/')}",
                room_id=room.id
            ))

        for i, room in enumerate(doble_rooms):
            image_name = doble_images[i % len(doble_images)]
            images.append(Image(
                url=f"/{os.path.join(STATIC_DIR, IMAGES_DIR, image_name).replace(os.sep, '/')}",
                room_id=room.id
            ))

        for i, room in enumerate(familiar_rooms):
            image_name = familiar_images[i % len(familiar_images)]
            images.append(Image(
                url=f"/{os.path.join(STATIC_DIR, IMAGES_DIR, image_name).replace(os.sep, '/')}",
                room_id=room.id
            ))

    db.add_all(images)
    await db.flush()

    # Reseñas
    reviews = [
        Review(
            accommodation_id=hotel_poblado.id,
            user_username="maria",
            rating=5,
            comment="Una experiencia de lujo increíble. Las instalaciones son modernas y el personal súper atento. ¡Volveré!",
            created_at=datetime.utcnow() - timedelta(days=randint(0, 30))
        ),
        Review(
            accommodation_id=hotel_poblado.id,
            user_username="sofia",
            rating=4,
            comment="Habitaciones elegantes y ubicación perfecta en El Poblado, pero el desayuno podría tener más variedad.",
            created_at=datetime.utcnow() - timedelta(days=randint(31, 90))
        ),
        Review(
            accommodation_id=hotel_poblado.id,
            user_username="sofia",
            rating=3,
            comment="Buen hotel, pero el ruido de la calle por la noche fue molesto. El servicio es excelente.",
            created_at=datetime.utcnow() - timedelta(days=randint(91, 180))
        ),
        Review(
            accommodation_id=hotel_tequendama.id,
            user_username="juan",
            rating=5,
            comment="Un clásico con mucho encanto. La arquitectura histórica y el servicio impecable hicieron mi estancia memorable.",
            created_at=datetime.utcnow() - timedelta(days=randint(0, 30))
        ),
        Review(
            accommodation_id=hotel_tequendama.id,
            user_username="laura",
            rating=4,
            comment="Gran experiencia en un hotel icónico. El wifi es un poco lento, pero el personal lo compensa con amabilidad.",
            created_at=datetime.utcnow() - timedelta(days=randint(31, 90))
        ),
        Review(
            accommodation_id=hotel_tequendama.id,
            user_username="admin",
            rating=4,
            comment="Ubicación céntrica y habitaciones cómodas. Algunas áreas necesitan renovación, pero el ambiente es único.",
            created_at=datetime.utcnow() - timedelta(days=randint(91, 180))
        ),
        Review(
            accommodation_id=hotel_casa_luz.id,
            user_username="pedro",
            rating=5,
            comment="Vistas al mar espectaculares y un ambiente íntimo. El desayuno en la terraza fue lo mejor. ¡Recomendado!",
            created_at=datetime.utcnow() - timedelta(days=randint(0, 30))
        ),
        Review(
            accommodation_id=hotel_casa_luz.id,
            user_username="maria",
            rating=4,
            comment="Hotel boutique encantador con excelente ubicación. El aire acondicionado en mi habitación era algo ruidoso.",
            created_at=datetime.utcnow() - timedelta(days=randint(31, 90))
        ),
        Review(
            accommodation_id=hotel_casa_luz.id,
            user_username="juan",
            rating=4,
            comment="El diseño del hotel es hermoso y el personal muy atento. El estacionamiento es limitado, pero manejable.",
            created_at=datetime.utcnow() - timedelta(days=randint(91, 180))
        ),
        Review(
            accommodation_id=hotel_verde_valle.id,
            user_username="sofia",
            rating=5,
            comment="Un oasis ecológico en Cali. Las áreas verdes y la sostenibilidad del hotel me encantaron. ¡Súper relajante!",
            created_at=datetime.utcnow() - timedelta(days=randint(0, 30))
        ),
        Review(
            accommodation_id=hotel_verde_valle.id,
            user_username="juan",
            rating=4,
            comment="Ambiente tranquilo y compromiso con el medio ambiente. La señal wifi en las habitaciones es débil.",
            created_at=datetime.utcnow() - timedelta(days=randint(31, 90))
        ),
        Review(
            accommodation_id=hotel_verde_valle.id,
            user_username="laura",
            rating=3,
            comment="Concepto ecológico interesante, pero el agua caliente en la ducha era inconsistente. Personal muy amable.",
            created_at=datetime.utcnow() - timedelta(days=randint(91, 180))
        ),
        Review(
            accommodation_id=hotel_jardin_secreto.id,
            user_username="pedro",
            rating=5,
            comment="Los jardines son un sueño y el ambiente es perfecto para desconectar. El mejor lugar en Medellín.",
            created_at=datetime.utcnow() - timedelta(days=randint(0, 30))
        ),
        Review(
            accommodation_id=hotel_jardin_secreto.id,
            user_username="pedro",
            rating=4,
            comment="Hermosos jardines y habitaciones acogedoras. El acceso al transporte público podría ser más conveniente.",
            created_at=datetime.utcnow() - timedelta(days=randint(31, 90))
        ),
        Review(
            accommodation_id=hotel_jardin_secreto.id,
            user_username="maria",
            rating=4,
            comment="Un lugar muy tranquilo, ideal para descansar. El desayuno es bueno, pero esperaba más opciones locales.",
            created_at=datetime.utcnow() - timedelta(days=randint(91, 180))
        ),
        Review(
            accommodation_id=hotel_cielo_abierto.id,
            user_username="maria",
            rating=5,
            comment="Vistas panorámicas impresionantes y un diseño moderno. El servicio es de primera clase. ¡Volveré pronto!",
            created_at=datetime.utcnow() - timedelta(days=randint(0, 30))
        ),
        Review(
            accommodation_id=hotel_cielo_abierto.id,
            user_username="sofia",
            rating=4,
            comment="Hotel moderno con vistas espectaculares. El ruido del tráfico en las noches altas puede ser molesto.",
            created_at=datetime.utcnow() - timedelta(days=randint(31, 90))
        ),
        Review(
            accommodation_id=hotel_cielo_abierto.id,
            user_username="juan",
            rating=4,
            comment="Habitaciones amplias y vistas increíbles de Bogotá. El check-in fue un poco lento, pero el resto excelente.",
            created_at=datetime.utcnow() - timedelta(days=randint(91, 180))
        ),
    ]
    db.add_all(reviews)
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
    print("Database seeded successfully with all Colombian departments, municipalities, accommodations, rooms, reservations, images, and maintenances!")