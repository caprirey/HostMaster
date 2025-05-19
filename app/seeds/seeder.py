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
from random import randint, shuffle, sample, choice

async def seed_database(db: AsyncSession):
    result = await db.execute(select(UserTable))
    if result.scalars().first():
        print("Database already seeded, skipping...")
        return

    # Usuarios
    users = []
    used_documents = set()
    used_phones = set()

    # Administrador
    users.append(UserTable(
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
    ))
    used_documents.add("1234567890")
    used_phones.add("+573183894217")

    # Empleados (15 total: 3 por alojamiento para 4 alojamientos, 2 para 2 alojamientos)
    employee_data = [
        ("camilo_prieto", "Camilo Prieto", "Camilo", "Prieto", "4567891230", "camilo", "+573044315484", ["poblado", "jardin"]),
        ("andrea_molina", "Andrea Molina Sánchez", "Andrea", "Molina Sánchez", "5678901234", "andrea123", "+573044315600", ["poblado"]),
        ("felipe_ortiz", "Felipe Ortiz Ramírez", "Felipe", "Ortiz Ramírez", "6789012345", "felipe123", "+573044315601", ["poblado"]),
        ("valentina_gomez", "Valentina Gómez Torres", "Valentina", "Gómez Torres", "7890123456", "valentina123", "+573044315602", ["tequendama"]),
        ("santiago_lopez", "Santiago López Díaz", "Santiago", "López Díaz", "8901234567", "santiago123", "+573044315603", ["tequendama"]),
        ("isabela_martinez", "Isabela Martínez Castro", "Isabela", "Martínez Castro", "9012345678", "isabela123", "+573044315604", ["tequendama"]),
        ("juan_castro", "Juan David Castro", "Juan", "Castro", "0123456789", "juan123", "+573044315605", ["casa_luz"]),
        ("laura_vargas", "Laura Sofía Vargas", "Laura", "Vargas", "1234567891", "laura123", "+573044315606", ["casa_luz"]),
        ("diego_ramos", "Diego Alejandro Ramos", "Diego", "Ramos", "2345678901", "diego123", "+573044315607", ["casa_luz"]),
        ("maria_fernandez", "María Juliana Fernández", "María", "Fernández", "3456789012", "maria123", "+573044315608", ["verde_valle"]),
        ("sebastian_moreno", "Sebastián Andrés Moreno", "Sebastián", "Moreno", "4567890123", "sebastian123", "+573044315609", ["verde_valle"]),
        ("camila_silva", "Camila Andrea Silva", "Camila", "Silva", "5678901235", "camila123", "+573044315610", ["verde_valle"]),
        ("nicolas_arias", "Nicolás Esteban Arias", "Nicolás", "Arias", "6789012346", "nicolas123", "+573044315611", ["jardin"]),
        ("paula_jimenez", "Paula Alejandra Jiménez", "Paula", "Jiménez", "7890123457", "paula123", "+573044315612", ["cielo"]),
        ("samuel_gutierrez", "Samuel David Gutiérrez", "Samuel", "Gutiérrez", "8901234568", "samuel123", "+573044315613", ["cielo"]),
    ]

    for i, (username, full_name, firstname, lastname, doc, password, phone, _) in enumerate(employee_data):
        if doc not in used_documents and phone not in used_phones:
            users.append(UserTable(
                username=username,
                email=f"{username}@yopmail.com",
                full_name=full_name,
                firstname=firstname,
                lastname=lastname,
                document_number=doc,
                hashed_password=get_password_hash(password),
                disabled=False,
                role="employee",
                image=f"/{os.path.join(STATIC_DIR, 'users', 'user_hombre.jpg' if i % 2 == 0 else 'user_mujer.jpg').replace(os.sep, '/')}",
                phone_number=phone
            ))
            used_documents.add(doc)
            used_phones.add(phone)

    # Clientes (33)
    client_data = [
        ("maria_lopez", "María Fernanda López", "María", "López", "9876543210", "maria", "+573112512612"),
        ("juan_perez", "Juan David Pérez", "Juan", "Pérez", "1122334455", "juan123", "+573044315490"),
        ("sofia_garcia", "Sofía Alejandra García", "Sofía", "García", "2233445566", "sofia123", "+573044315491"),
        ("pedro_martinez", "Pedro Antonio Martínez", "Pedro", "Martínez", "3344556677", "pedro123", "+573044315492"),
        ("laura_rodriguez", "Laura Valentina Rodríguez", "Laura", "Rodríguez", "4455667788", "laura123", "+573044315493"),
        ("diego_sanchez", "Diego Armando Sánchez", "Diego", "Sánchez", "5566778899", "diego123", "+573044315494"),
        ("ana_torres", "Ana María Torres", "Ana", "Torres", "6677889900", "ana123", "+573044315495"),
        ("carlos_diaz", "Carlos Eduardo Díaz", "Carlos", "Díaz", "7788990011", "carlos123", "+573044315496"),
        ("luisa_hernandez", "Luisa Fernanda Hernández", "Luisa", "Hernández", "8899001122", "luisa123", "+573044315497"),
        ("mateo_gonzalez", "Mateo Andrés González", "Mateo", "González", "9900112233", "mateo123", "+573044315498"),
        ("camila_ortiz", "Camila Sofía Ortiz", "Camila", "Ortiz", "1011223344", "camila123", "+573044315499"),
        ("sebastian_molina", "Sebastián Felipe Molina", "Sebastián", "Molina", "1122334456", "sebastian123", "+573044315500"),
        ("valeria_castro", "Valeria Isabel Castro", "Valeria", "Castro", "1233445567", "valeria123", "+573044315501"),
        ("gabriel_vega", "Gabriel Alejandro Vega", "Gabriel", "Vega", "1344556678", "gabriel123", "+573044315502"),
        ("isabella_ramos", "Isabella Victoria Ramos", "Isabella", "Ramos", "1455667789", "isabella123", "+573044315503"),
        ("andres_moreno", "Andrés Felipe Moreno", "Andrés", "Moreno", "1566778890", "andres123", "+573044315504"),
        ("juliana_silva", "Juliana Andrea Silva", "Juliana", "Silva", "1677889901", "juliana123", "+573044315505"),
        ("nicolas_arias_client", "Nicolás Esteban Arias", "Nicolás", "Arias", "1788990012", "nicolas123", "+573044315506"),
        ("paula_jimenez_client", "Paula Alejandra Jiménez", "Paula", "Jiménez", "1899001123", "paula123", "+573044315507"),
        ("samuel_gutierrez_client", "Samuel David Gutiérrez", "Samuel", "Gutiérrez", "1900112234", "samuel123", "+573044315508"),
        ("daniela_fernandez", "Daniela Sofía Fernández", "Daniela", "Fernández", "2011223345", "daniela123", "+573044315509"),
        ("tomas_aguilar", "Tomás Ignacio Aguilar", "Tomás", "Aguilar", "2122334456", "tomas123", "+573044315510"),
        ("emma_vargas", "Emma Valentina Vargas", "Emma", "Vargas", "2233445567", "emma123", "+573044315511"),
        ("jose_cardenas", "José Miguel Cárdenas", "José", "Cárdenas", "2344556678", "jose123", "+573044315512"),
        ("sara_lopez", "Sara Camila López", "Sara", "López", "2455667789", "sara123", "+573044315513"),
        ("miguel_angel", "Miguel Ángel Ramírez", "Miguel", "Ramírez", "2566778890", "miguel123", "+573044315514"),
        ("sofia_mora", "Sofía Elena Mora", "Sofía", "Mora", "2677889901", "sofia_m123", "+573044315515"),
        ("javier_pena", "Javier Andrés Peña", "Javier", "Peña", "2788990012", "javier123", "+573044315516"),
        ("mariana_gil", "Mariana Isabel Gil", "Mariana", "Gil", "2899001123", "mariana123", "+573044315517"),
        ("esteban_quiroz", "Esteban Camilo Quiroz", "Esteban", "Quiroz", "2900112234", "esteban123", "+573044315518"),
        ("clara_montes", "Clara Valentina Montes", "Clara", "Montes", "3011223345", "clara123", "+573044315519"),
        ("david_ospina", "David Alejandro Ospina", "David", "Ospina", "3122334456", "david123", "+573044315520"),
        ("lucia_mendez", "Lucía Fernanda Méndez", "Lucía", "Méndez", "3233445567", "lucia123", "+573044315521"),
    ]

    for i, (username, full_name, firstname, lastname, doc, password, phone) in enumerate(client_data):
        if doc not in used_documents and phone not in used_phones:
            users.append(UserTable(
                username=username,
                email=f"{username}@yopmail.com",
                full_name=full_name,
                firstname=firstname,
                lastname=lastname,
                document_number=doc,
                hashed_password=get_password_hash(password),
                disabled=False,
                role="client",
                image=f"/{os.path.join(STATIC_DIR, 'users', 'user_hombre.jpg' if i % 2 == 0 else 'user_mujer.jpg').replace(os.sep, '/')}",
                phone_number=phone
            ))
            used_documents.add(doc)
            used_phones.add(phone)

    db.add_all(users)
    await db.flush()
    print(f"Usuarios creados: {len(users)} (1 admin, {len(employee_data)} empleados, {len(client_data)} clientes)")

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
    print("País y ciudades creados")

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
    print("Alojamientos creados")

    # Asociar usuarios a alojamientos
    accommodation_mapping = {
        "poblado": hotel_poblado.id,
        "tequendama": hotel_tequendama.id,
        "casa_luz": hotel_casa_luz.id,
        "verde_valle": hotel_verde_valle.id,
        "jardin": hotel_jardin_secreto.id,
        "cielo": hotel_cielo_abierto.id
    }
    user_accommodation_entries = []
    for username, _, _, _, _, _, _, hotels in employee_data:
        for hotel in hotels:
            user_accommodation_entries.append({
                "user_username": username,
                "accommodation_id": accommodation_mapping[hotel]
            })

    await db.execute(
        insert(Accommodation.__table__.metadata.tables['user_accommodation']),
        user_accommodation_entries
    )
    await db.flush()
    print(f"Asignaciones de empleados creadas: {len(user_accommodation_entries)}")

    # Tipos de habitación
    sencilla = RoomType(name="Habitación Sencilla", max_guests=1, description="Habitación con cama sencilla")
    doble = RoomType(name="Habitación Doble", max_guests=2, description="Habitación con cama doble")
    familiar = RoomType(name="Habitación Familiar", max_guests=4, description="Habitación con dos camas dobles")
    db.add_all([sencilla, doble, familiar])
    await db.flush()
    print("Tipos de habitación creados")

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
    print("Servicios extra creados")

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
    print(f"Habitaciones creadas: {len(rooms)}")

    # Reservas y Servicios Extra
    reservations = []
    reservation_extra_entries = []
    client_usernames = [data[0] for data in client_data]  # Lista de 33 usernames
    print(f"Clientes disponibles para reservas: {len(client_usernames)}")
    accommodations = [hotel_poblado, hotel_tequendama, hotel_casa_luz, hotel_verde_valle, hotel_jardin_secreto, hotel_cielo_abierto]
    start_month = date(2025, 5, 1)
    end_month = date(2025, 5, 31)
    max_reservations_per_day = 5  # Máximo de reservas por día por alojamiento
    extra_services = [breakfast, parking, wifi, spa]  # Servicios extra disponibles

    for accom in accommodations:
        accom_rooms = [r for r in rooms if r.accommodation_id == accom.id]
        print(f"Procesando reservas para {accom.name} con {len(accom_rooms)} habitaciones")
        room_availability = {room.id: [] for room in accom_rooms}

        for day in range((end_month - start_month).days + 1):
            current_date = start_month + timedelta(days=day)
            available_rooms = [
                room for room in accom_rooms
                if all(
                    current_date > reserved_end or (current_date + timedelta(days=1)) < reserved_start
                    for reserved_start, reserved_end in room_availability[room.id]
                )
            ]
            if not available_rooms:
                print(f"  Día {current_date}: No hay habitaciones disponibles")
                continue

            num_reservations = randint(1, min(max_reservations_per_day, len(available_rooms)))
            print(f"  Día {current_date}: Intentando crear {num_reservations} reservas")

            selected_rooms = sample(available_rooms, num_reservations)

            for room in selected_rooms:
                stay_length = randint(1, 7)
                start_date = current_date
                end_date = min(start_date + timedelta(days=stay_length), end_month)

                guest_count = 1 if room.type_id == sencilla.id else (2 if room.type_id == doble.id else 4)
                status = "confirmed" if randint(1, 100) <= 90 else "pending"

                reservation = Reservation(
                    user_username=choice(client_usernames),
                    room_id=room.id,
                    accommodation_id=accom.id,
                    start_date=start_date,
                    end_date=end_date,
                    guest_count=guest_count,
                    status=status,
                    observations=f"Reserva para habitación {room.number} en {accom.name} desde {start_date}"
                )
                reservations.append(reservation)
                room_availability[room.id].append((start_date, end_date))
                print(f"  Día {current_date}: Reserva creada para habitación {room.number} ({start_date} a {end_date})")

                if randint(1, 100) <= 50:
                    num_services = randint(1, 2)
                    selected_services = sample(extra_services, num_services)
                    for service in selected_services:
                        reservation_extra_entries.append({
                            "reservation_id": None,
                            "extra_service_id": service.id
                        })

    print(f"Total de reservas creadas: {len(reservations)}")
    db.add_all(reservations)
    await db.flush()
    print("Reservas insertadas en la base de datos")

    print(f"Servicios extra a asignar: {len(reservation_extra_entries)}")
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
    print("Servicios extra asignados")

    # Mantenimientos
    maintenances = [
        Maintenance(
            description="Reparar aire acondicionado",
            status=MaintenanceStatus.PENDING,
            priority=MaintenancePriority.HIGH,
            room_id=[r.id for r in rooms if r.accommodation_id == hotel_poblado.id and r.number == "101"][0],
            accommodation_id=hotel_poblado.id,
            created_by="camilo_prieto",
            assigned_to="camilo_prieto",
            created_at=date(2025, 5, 17),
            updated_at=date(2025, 5, 17)
        ),
        Maintenance(
            description="Reemplazar bombilla fundida",
            status=MaintenanceStatus.IN_PROGRESS,
            priority=MaintenancePriority.MEDIUM,
            room_id=[r.id for r in rooms if r.accommodation_id == hotel_tequendama.id and r.number == "205"][0],
            accommodation_id=hotel_tequendama.id,
            created_by="valentina_gomez",
            assigned_to="valentina_gomez",
            created_at=date(2025, 5, 15),
            updated_at=date(2025, 5, 17)
        ),
        Maintenance(
            description="Limpiar alfombra manchada",
            status=MaintenanceStatus.PENDING,
            priority=MaintenancePriority.LOW,
            room_id=[r.id for r in rooms if r.accommodation_id == hotel_casa_luz.id and r.number == "108"][0],
            accommodation_id=hotel_casa_luz.id,
            created_by="juan_castro",
            assigned_to="juan_castro",
            created_at=date(2025, 5, 12),
            updated_at=date(2025, 5, 17)
        ),
    ]
    db.add_all(maintenances)
    await db.flush()
    print("Mantenimientos creados")

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
        "habitacion_sencilla_3.jpg",
        "habitacion_sencilla_4.jpg"
    ]
    doble_images = [
        "habitacion_doble_0.jpg",
        "habitacion_doble_1.jpg",
        "habitacion_doble_2.jpg",
        "habitacion_doble_3.jpg",
        "habitacion_doble_4.jpg"
    ]
    familiar_images = [
        "habitacion_familiar_0.jpg",
        "habitacion_familiar_1.jpg",
        "habitacion_familiar_2.jpg",
        "habitacion_familiar_3.jpg",
        "habitacion_familiar_4.jpg"
    ]

    for accom in accommodations:
        accom_rooms = [r for r in rooms if r.accommodation_id == accom.id]
        sencilla_rooms = [r for r in accom_rooms if r.type_id == sencilla.id]
        doble_rooms = [r for r in accom_rooms if r.type_id == doble.id]
        familiar_rooms = [r for r in accom_rooms if r.type_id == familiar.id]

        # Asignar las 5 imágenes a cada habitación sencilla
        for room in sencilla_rooms:
            for image_name in sencilla_images:
                images.append(Image(
                    url=f"/{os.path.join(STATIC_DIR, IMAGES_DIR, image_name).replace(os.sep, '/')}",
                    room_id=room.id
                ))

        # Asignar las 5 imágenes a cada habitación doble
        for room in doble_rooms:
            for image_name in doble_images:
                images.append(Image(
                    url=f"/{os.path.join(STATIC_DIR, IMAGES_DIR, image_name).replace(os.sep, '/')}",
                    room_id=room.id
                ))

        # Asignar las 5 imágenes a cada habitación familiar
        for room in familiar_rooms:
            for image_name in familiar_images:
                images.append(Image(
                    url=f"/{os.path.join(STATIC_DIR, IMAGES_DIR, image_name).replace(os.sep, '/')}",
                    room_id=room.id
                ))

    db.add_all(images)
    await db.flush()
    print("Imágenes creadas")

    # Reseñas
    reviews = [
        Review(
            accommodation_id=hotel_poblado.id,
            user_username=choice(client_usernames),
            rating=5,
            comment="Una experiencia de lujo increíble. Las instalaciones son modernas y el personal súper atento. ¡Volveré!",
            created_at=datetime.utcnow() - timedelta(days=randint(0, 30))
        ),
        Review(
            accommodation_id=hotel_poblado.id,
            user_username=choice(client_usernames),
            rating=4,
            comment="Habitaciones elegantes y ubicación perfecta en El Poblado, pero el desayuno podría tener más variedad.",
            created_at=datetime.utcnow() - timedelta(days=randint(31, 90))
        ),
        Review(
            accommodation_id=hotel_poblado.id,
            user_username=choice(client_usernames),
            rating=3,
            comment="Buen hotel, pero el ruido de la calle por la noche fue molesto. El servicio es excelente.",
            created_at=datetime.utcnow() - timedelta(days=randint(91, 180))
        ),
        Review(
            accommodation_id=hotel_tequendama.id,
            user_username=choice(client_usernames),
            rating=5,
            comment="Un clásico con mucho encanto. La arquitectura histórica y el servicio impecable hicieron mi estancia memorable.",
            created_at=datetime.utcnow() - timedelta(days=randint(0, 30))
        ),
        Review(
            accommodation_id=hotel_tequendama.id,
            user_username=choice(client_usernames),
            rating=4,
            comment="Gran experiencia en un hotel icónico. El wifi es un poco lento, pero el personal lo compensa con amabilidad.",
            created_at=datetime.utcnow() - timedelta(days=randint(31, 90))
        ),
        Review(
            accommodation_id=hotel_tequendama.id,
            user_username=choice(client_usernames),
            rating=4,
            comment="Ubicación céntrica y habitaciones cómodas. Algunas áreas necesitan renovación, pero el ambiente es único.",
            created_at=datetime.utcnow() - timedelta(days=randint(91, 180))
        ),
        Review(
            accommodation_id=hotel_casa_luz.id,
            user_username=choice(client_usernames),
            rating=5,
            comment="Vistas al mar espectaculares y un ambiente íntimo. El desayuno en la terraza fue lo mejor. ¡Recomendado!",
            created_at=datetime.utcnow() - timedelta(days=randint(0, 30))
        ),
        Review(
            accommodation_id=hotel_casa_luz.id,
            user_username=choice(client_usernames),
            rating=4,
            comment="Hotel boutique encantador con excelente ubicación. El aire acondicionado en mi habitación era algo ruidoso.",
            created_at=datetime.utcnow() - timedelta(days=randint(31, 90))
        ),
        Review(
            accommodation_id=hotel_casa_luz.id,
            user_username=choice(client_usernames),
            rating=4,
            comment="El diseño del hotel es hermoso y el personal muy atento. El estacionamiento es limitado, pero manejable.",
            created_at=datetime.utcnow() - timedelta(days=randint(91, 180))
        ),
        Review(
            accommodation_id=hotel_verde_valle.id,
            user_username=choice(client_usernames),
            rating=5,
            comment="Un oasis ecológico en Cali. Las áreas verdes y la sostenibilidad del hotel me encantaron. ¡Súper relajante!",
            created_at=datetime.utcnow() - timedelta(days=randint(0, 30))
        ),
        Review(
            accommodation_id=hotel_verde_valle.id,
            user_username=choice(client_usernames),
            rating=4,
            comment="Ambiente tranquilo y compromiso con el medio ambiente. La señal wifi en las habitaciones es débil.",
            created_at=datetime.utcnow() - timedelta(days=randint(31, 90))
        ),
        Review(
            accommodation_id=hotel_verde_valle.id,
            user_username=choice(client_usernames),
            rating=3,
            comment="Concepto ecológico interesante, pero el agua caliente en la ducha era inconsistente. Personal muy amable.",
            created_at=datetime.utcnow() - timedelta(days=randint(91, 180))
        ),
        Review(
            accommodation_id=hotel_jardin_secreto.id,
            user_username=choice(client_usernames),
            rating=5,
            comment="Los jardines son un sueño y el ambiente es perfecto para desconectar. El mejor lugar en Medellín.",
            created_at=datetime.utcnow() - timedelta(days=randint(0, 30))
        ),
        Review(
            accommodation_id=hotel_jardin_secreto.id,
            user_username=choice(client_usernames),
            rating=4,
            comment="Hermosos jardines y habitaciones acogedoras. El acceso al transporte público podría ser más conveniente.",
            created_at=datetime.utcnow() - timedelta(days=randint(31, 90))
        ),
        Review(
            accommodation_id=hotel_jardin_secreto.id,
            user_username=choice(client_usernames),
            rating=4,
            comment="Un lugar muy tranquilo, ideal para descansar. El desayuno es bueno, pero esperaba más opciones locales.",
            created_at=datetime.utcnow() - timedelta(days=randint(91, 180))
        ),
        Review(
            accommodation_id=hotel_cielo_abierto.id,
            user_username=choice(client_usernames),
            rating=5,
            comment="Vistas panorámicas impresionantes y un diseño moderno. El servicio es de primera clase. ¡Volveré pronto!",
            created_at=datetime.utcnow() - timedelta(days=randint(0, 30))
        ),
        Review(
            accommodation_id=hotel_cielo_abierto.id,
            user_username=choice(client_usernames),
            rating=4,
            comment="Hotel moderno con vistas espectaculares. El ruido del tráfico en las noches altas puede ser molesto.",
            created_at=datetime.utcnow() - timedelta(days=randint(31, 90))
        ),
        Review(
            accommodation_id=hotel_cielo_abierto.id,
            user_username=choice(client_usernames),
            rating=4,
            comment="Habitaciones amplias y vistas increíbles de Bogotá. El check-in fue un poco lento, pero el resto excelente.",
            created_at=datetime.utcnow() - timedelta(days=randint(91, 180))
        ),
    ]
    db.add_all(reviews)
    await db.flush()
    print("Reseñas creadas")

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
    print("Productos creados")

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
    print("Inventario de habitaciones creado")

    await db.commit()
    print("Database seeded successfully with all Colombian departments, municipalities, accommodations, rooms, reservations, images, and maintenances!")