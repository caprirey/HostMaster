import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from unittest.mock import AsyncMock
from datetime import date, timedelta
from app.main import app
from app.models.sqlalchemy_models import Base, UserTable, Accommodation, Room, Reservation, ExtraService, user_accommodation
from app.models.pydantic_models import AccommodationBase, AccommodationUpdate, ReservationBase, ReservationUpdate, ExtraServiceCreate, ExtraServiceUpdate
from app.utils.auth import get_password_hash

# Configuración de la base de datos en memoria
DATABASE_URL = "sqlite+aiosqlite:///:memory:"
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Configuración del cliente de prueba
client = TestClient(app)

# Fixture para inicializar la base de datos
@pytest_asyncio.fixture(scope="function")
async def db_session():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

# Fixture para simular usuarios
@pytest_asyncio.fixture
def mock_user():
    user = AsyncMock()
    return user

# Helper para crear un usuario en la base de datos
async def create_test_user(db: AsyncSession, username: str, role: str):
    user = UserTable(
        username=username,
        email=f"{username}@hotelescolombia.com",
        full_name=f"{username.capitalize()} Test",
        firstname=username.capitalize(),
        lastname="Test",
        document_number=f"1234567890{username}",
        hashed_password=get_password_hash("password123"),
        disabled=False,
        role=role,
        image=f"static/images/{username}.jpg"
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

# Helper para crear un alojamiento en la base de datos
async def create_test_accommodation(db: AsyncSession, city_id: int, username: str):
    accommodation = Accommodation(
        name="Test Hotel",
        city_id=city_id,
        address="123 Test Street",
        information="Test accommodation"
    )
    db.add(accommodation)
    await db.commit()
    await db.refresh(accommodation)
    # Asociar usuario al alojamiento
    await db.execute(
        user_accommodation.insert().values(
            user_username=username,
            accommodation_id=accommodation.id
        )
    )
    await db.commit()
    return accommodation

# Helper para crear una habitación en la base de datos
async def create_test_room(db: AsyncSession, accommodation_id: int, type_id: int):
    room = Room(
        accommodation_id=accommodation_id,
        type_id=type_id,
        number="101",
        price=100000,
        isAvailable=True
    )
    db.add(room)
    await db.commit()
    await db.refresh(room)
    return room

# Helper para crear un servicio extra en la base de datos
async def create_test_extra_service(db: AsyncSession):
    extra_service = ExtraService(
        name="Test Service",
        description="Test extra service",
        price=20000
    )
    db.add(extra_service)
    await db.commit()
    await db.refresh(extra_service)
    return extra_service

# Sobreescribir dependencias
@pytest_asyncio.fixture(autouse=True)
async def override_dependencies(db_session, mock_user):
    async def override_get_db():
        yield db_session

    async def override_get_current_active_user():
        return mock_user

    app.dependency_overrides[Depends(get_db)] = override_get_db
    app.dependency_overrides[Depends(get_current_active_user)] = override_get_current_active_user
    yield
    app.dependency_overrides.clear()

# Pruebas para Accommodations
@pytest.mark.asyncio
async def test_create_accommodation_admin(db_session: AsyncSession, mock_user):
    # Configurar usuario admin
    admin = await create_test_user(db_session, "admin", "admin")
    mock_user.username = admin.username
    mock_user.role = admin.role

    # Datos para crear alojamiento
    accommodation_data = {
        "name": "Test Hotel",
        "city_id": 1,
        "address": "123 Test Street",
        "information": "A test hotel"
    }

    # Hacer solicitud
    response = client.post("/hotel/accommodations/", json=accommodation_data)

    # Verificar respuesta
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == accommodation_data["name"]
    assert data["city_id"] == accommodation_data["city_id"]

@pytest.mark.asyncio
async def test_create_accommodation_unauthorized_client(db_session: AsyncSession, mock_user):
    # Configurar usuario client
    client_user = await create_test_user(db_session, "maria", "client")
    mock_user.username = client_user.username
    mock_user.role = client_user.role

    # Datos para crear alojamiento
    accommodation_data = {
        "name": "Test Hotel",
        "city_id": 1,
        "address": "123 Test Street",
        "information": "A test hotel"
    }

    # Hacer solicitud
    response = client.post("/hotel/accommodations/", json=accommodation_data)

    # Verificar error de permisos
    assert response.status_code == 403
    assert response.json()["detail"] == "Only admin or employee roles can create accommodations"

@pytest.mark.asyncio
async def test_get_accommodations_admin(db_session: AsyncSession, mock_user):
    # Configurar usuario admin
    admin = await create_test_user(db_session, "admin", "admin")
    mock_user.username = admin.username
    mock_user.role = admin.role

    # Crear alojamiento
    await create_test_accommodation(db_session, city_id=1, username=admin.username)

    # Hacer solicitud
    response = client.get("/hotel/accommodations/")

    # Verificar respuesta
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["name"] == "Test Hotel"

@pytest.mark.asyncio
async def test_update_accommodation_admin(db_session: AsyncSession, mock_user):
    # Configurar usuario admin
    admin = await create_test_user(db_session, "admin", "admin")
    mock_user.username = admin.username
    mock_user.role = admin.role

    # Crear alojamiento
    accommodation = await create_test_accommodation(db_session, city_id=1, username=admin.username)

    # Datos para actualizar
    update_data = {
        "name": "Updated Hotel",
        "information": "Updated information"
    }

    # Hacer solicitud
    response = client.patch(f"/hotel/accommodations/{accommodation.id}", json=update_data)

    # Verificar respuesta
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Hotel"
    assert data["information"] == "Updated information"

@pytest.mark.asyncio
async def test_delete_accommodation_admin(db_session: AsyncSession, mock_user):
    # Configurar usuario admin
    admin = await create_test_user(db_session, "admin", "admin")
    mock_user.username = admin.username
    mock_user.role = admin.role

    # Crear alojamiento
    accommodation = await create_test_accommodation(db_session, city_id=1, username=admin.username)

    # Hacer solicitud
    response = client.delete(f"/hotel/accommodations/{accommodation.id}")

    # Verificar respuesta
    assert response.status_code == 204

    # Verificar que el alojamiento fue eliminado
    response = client.get(f"/hotel/accommodations/{accommodation.id}")
    assert response.status_code == 404

# Pruebas para Reservations
@pytest.mark.asyncio
async def test_create_reservation_client(db_session: AsyncSession, mock_user):
    # Configurar usuario client
    client_user = await create_test_user(db_session, "maria", "client")
    mock_user.username = client_user.username
    mock_user.role = client_user.role

    # Crear alojamiento y habitación
    accommodation = await create_test_accommodation(db_session, city_id=1, username=client_user.username)
    room = await create_test_room(db_session, accommodation_id=accommodation.id, type_id=1)

    # Datos para crear reserva
    reservation_data = {
        "room_id": room.id,
        "accommodation_id": accommodation.id,
        "start_date": "2025-06-01",
        "end_date": "2025-06-04",
        "guest_count": 2,
        "status": "confirmed",
        "observations": "Test reservation"
    }

    # Hacer solicitud
    response = client.post("/hotel/reservations/", json=reservation_data)

    # Verificar respuesta
    assert response.status_code == 200
    data = response.json()
    assert data["room_id"] == room.id
    assert data["user_username"] == client_user.username
    assert data["status"] == "confirmed"

@pytest.mark.asyncio
async def test_get_reservations_client(db_session: AsyncSession, mock_user):
    # Configurar usuario client
    client_user = await create_test_user(db_session, "maria", "client")
    mock_user.username = client_user.username
    mock_user.role = client_user.role

    # Crear alojamiento, habitación y reserva
    accommodation = await create_test_accommodation(db_session, city_id=1, username=client_user.username)
    room = await create_test_room(db_session, accommodation_id=accommodation.id, type_id=1)
    reservation = Reservation(
        user_username=client_user.username,
        room_id=room.id,
        accommodation_id=accommodation.id,
        start_date=date(2025, 6, 1),
        end_date=date(2025, 6, 4),
        guest_count=2,
        status="confirmed",
        observations="Test reservation"
    )
    db_session.add(reservation)
    await db_session.commit()

    # Hacer solicitud
    response = client.get("/hotel/reservations/")

    # Verificar respuesta
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["user_username"] == client_user.username
    assert data[0]["room_id"] == room.id

@pytest.mark.asyncio
async def test_update_reservation_client(db_session: AsyncSession, mock_user):
    # Configurar usuario client
    client_user = await create_test_user(db_session, "maria", "client")
    mock_user.username = client_user.username
    mock_user.role = client_user.role

    # Crear alojamiento, habitación y reserva
    accommodation = await create_test_accommodation(db_session, city_id=1, username=client_user.username)
    room = await create_test_room(db_session, accommodation_id=accommodation.id, type_id=1)
    reservation = Reservation(
        user_username=client_user.username,
        room_id=room.id,
        accommodation_id=accommodation.id,
        start_date=date(2025, 6, 1),
        end_date=date(2025, 6, 4),
        guest_count=2,
        status="confirmed",
        observations="Test reservation"
    )
    db_session.add(reservation)
    await db_session.commit()
    await db_session.refresh(reservation)

    # Datos para actualizar
    update_data = {
        "guest_count": 3,
        "observations": "Updated reservation"
    }

    # Hacer solicitud
    response = client.patch(f"/hotel/reservations/{reservation.id}", json=update_data)

    # Verificar respuesta
    assert response.status_code == 200
    data = response.json()
    assert data["guest_count"] == 3
    assert data["observations"] == "Updated reservation"

@pytest.mark.asyncio
async def test_delete_reservation_client(db_session: AsyncSession, mock_user):
    # Configurar usuario client
    client_user = await create_test_user(db_session, "maria", "client")
    mock_user.username = client_user.username
    mock_user.role = client_user.role

    # Crear alojamiento, habitación y reserva
    accommodation = await create_test_accommodation(db_session, city_id=1, username=client_user.username)
    room = await create_test_room(db_session, accommodation_id=accommodation.id, type_id=1)
    reservation = Reservation(
        user_username=client_user.username,
        room_id=room.id,
        accommodation_id=accommodation.id,
        start_date=date(2025, 6, 1),
        end_date=date(2025, 6, 4),
        guest_count=2,
        status="confirmed",
        observations="Test reservation"
    )
    db_session.add(reservation)
    await db_session.commit()
    await db_session.refresh(reservation)

    # Hacer solicitud
    response = client.delete(f"/hotel/reservations/{reservation.id}")

    # Verificar respuesta
    assert response.status_code == 204

    # Verificar que la reserva fue eliminada
    response = client.get(f"/hotel/reservations/{reservation.id}")
    assert response.status_code == 404

# Pruebas para Extra Services
@pytest.mark.asyncio
async def test_create_extra_service_admin(db_session: AsyncSession, mock_user):
    # Configurar usuario admin
    admin = await create_test_user(db_session, "admin", "admin")
    mock_user.username = admin.username
    mock_user.role = admin.role

    # Datos para crear servicio extra
    extra_service_data = {
        "name": "Test Service",
        "description": "Test extra service",
        "price": 20000
    }

    # Hacer solicitud
    response = client.post("/hotel/extra-services/", json=extra_service_data)

    # Verificar respuesta
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == extra_service_data["name"]
    assert data["price"] == extra_service_data["price"]

@pytest.mark.asyncio
async def test_get_all_extra_services_admin(db_session: AsyncSession, mock_user):
    # Configurar usuario admin
    admin = await create_test_user(db_session, "admin", "admin")
    mock_user.username = admin.username
    mock_user.role = admin.role

    # Crear servicio extra
    extra_service = await create_test_extra_service(db_session)

    # Hacer solicitud
    response = client.get("/hotel/extra-services/")

    # Verificar respuesta
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == extra_service.name

@pytest.mark.asyncio
async def test_get_extra_service_admin(db_session: AsyncSession, mock_user):
    # Configurar usuario admin
    admin = await create_test_user(db_session, "admin", "admin")
    mock_user.username = admin.username
    mock_user.role = admin.role

    # Crear servicio extra
    extra_service = await create_test_extra_service(db_session)

    # Hacer solicitud
    response = client.get(f"/hotel/extra-services/{extra_service.id}")

    # Verificar respuesta
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == extra_service.name
    assert data["id"] == extra_service.id

@pytest.mark.asyncio
async def test_update_extra_service_admin(db_session: AsyncSession, mock_user):
    # Configurar usuario admin
    admin = await create_test_user(db_session, "admin", "admin")
    mock_user.username = admin.username
    mock_user.role = admin.role

    # Crear servicio extra
    extra_service = await create_test_extra_service(db_session)

    # Datos para actualizar
    update_data = {
        "name": "Updated Service",
        "price": 25000
    }

    # Hacer solicitud
    response = client.patch(f"/hotel/extra-services/{extra_service.id}", json=update_data)

    # Verificar respuesta
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Service"
    assert data["price"] == 25000

@pytest.mark.asyncio
async def test_delete_extra_service_admin(db_session: AsyncSession, mock_user):
    # Configurar usuario admin
    admin = await create_test_user(db_session, "admin", "admin")
    mock_user.username = admin.username
    mock_user.role = admin.role

    # Crear servicio extra
    extra_service = await create_test_extra_service(db_session)

    # Hacer solicitud
    response = client.delete(f"/hotel/extra-services/{extra_service.id}")

    # Verificar respuesta
    assert response.status_code == 204

    # Verificar que el servicio extra fue eliminado
    response = client.get(f"/hotel/extra-services/{extra_service.id}")
    assert response.status_code == 404