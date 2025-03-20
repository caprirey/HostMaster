from fastapi import HTTPException, status, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.models.pydantic_models import (
    Accommodation,
    AccommodationBase,
    RoomType,
    RoomTypeBase,
    Room,
    RoomBase,
    ImageBase,
    Image,
    Reservation  # Añadido para get_available_rooms
)
from app.models.sqlalchemy_models import (
    Image as ImageTable,
    Accommodation as AccommodationTable,
    RoomType as RoomTypeTable,
    Room as RoomTable,
    UserTable,
    Reservation as ReservationTable,  # Añadido para get_available_rooms,
    City as CityTable,
)
import os
import uuid
from typing import List
from datetime import date  # Añadido para tipado de fechas
from app.config.settings import STATIC_DIR, IMAGES_DIR  # Importamos las rutas desde settings
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



async def get_accommodations(db: AsyncSession, username: str) -> list[Accommodation]:
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.role == "admin":
        result = await db.execute(
            select(AccommodationTable).options(selectinload(AccommodationTable.images))
        )
    elif user.role == "user":
        result = await db.execute(
            select(AccommodationTable)
            .where(AccommodationTable.created_by == username)
            .options(selectinload(AccommodationTable.images))
        )
    else:
        raise HTTPException(status_code=403, detail="Invalid role")

    accommodations = result.scalars().all()
    return [Accommodation.model_validate(accommodation) for accommodation in accommodations]

async def create_accommodation(
        db: AsyncSession,
        accommodation: AccommodationBase,
        username: str
) -> Accommodation:
    # Verificar que el usuario exista
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verificar que la ciudad exista
    result = await db.execute(
        select(CityTable).where(CityTable.id == accommodation.city_id)
    )
    city = result.scalar_one_or_none()
    if not city:
        raise HTTPException(status_code=404, detail="City not found")

    # Crear el alojamiento
    db_accommodation = AccommodationTable(
        name=accommodation.name,
        city_id=accommodation.city_id,
        created_by=username  # El creador es el usuario autenticado
    )
    db.add(db_accommodation)
    await db.commit()

    # Cargar la relación images para evitar problemas con Pydantic
    result = await db.execute(
        select(AccommodationTable)
        .where(AccommodationTable.id == db_accommodation.id)
        .options(selectinload(AccommodationTable.images))
    )
    db_accommodation = result.scalar_one()
    return Accommodation.model_validate(db_accommodation)

async def get_rooms(db: AsyncSession, username: str, accommodation_id: int) -> list[Room]:
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        select(AccommodationTable)
        .where(AccommodationTable.id == accommodation_id)
    )
    accommodation = result.scalar_one_or_none()
    if not accommodation:
        raise HTTPException(status_code=404, detail="Accommodation not found")

    if user.role == "admin":
        pass
    elif user.role == "user":
        if accommodation.created_by != username:
            raise HTTPException(status_code=403, detail="Not authorized to view rooms")
    else:
        raise HTTPException(status_code=403, detail="Invalid role")

    result = await db.execute(
        select(RoomTable)
        .where(RoomTable.accommodation_id == accommodation_id)
        .options(selectinload(RoomTable.images))
    )
    rooms = result.scalars().all()
    return [Room.model_validate(room) for room in rooms]

async def create_room_type(
        db: AsyncSession, room_type: RoomTypeBase, accommodation_id: int, username: str
) -> RoomType:
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        select(AccommodationTable).where(AccommodationTable.id == accommodation_id)
    )
    accommodation = result.scalar_one_or_none()
    if not accommodation:
        raise HTTPException(status_code=404, detail="Accommodation not found")

    if user.role != "admin" and accommodation.created_by != username:
        raise HTTPException(status_code=403, detail="Not authorized to add room type")

    db_room_type = RoomTypeTable(**room_type.model_dump(), accommodation_id=accommodation_id)
    db.add(db_room_type)
    await db.commit()
    await db.refresh(db_room_type)
    return RoomType.model_validate(db_room_type)

async def get_room_types(
        db: AsyncSession,
        username: str,
        accommodation_id: int | None = None
) -> List[RoomType]:
    # Verificar que el usuario exista (autenticación básica)
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Construir la consulta base
    query = select(RoomTypeTable)

    # Filtrar por accommodation_id si se proporciona
    if accommodation_id:
        query = query.where(RoomTypeTable.accommodation_id == accommodation_id)

    # Ejecutar la consulta
    result = await db.execute(query)
    room_types = result.scalars().all()

    if not room_types and accommodation_id:
        raise HTTPException(status_code=404, detail="No room types found for this accommodation")

    return [RoomType.model_validate(room_type) for room_type in room_types]


async def create_room(
        db: AsyncSession,
        room: RoomBase,
        username: str
) -> Room:
    # Verificar que el usuario exista
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verificar que el alojamiento exista
    result = await db.execute(
        select(AccommodationTable).where(AccommodationTable.id == room.accommodation_id)
    )
    accommodation = result.scalar_one_or_none()
    if not accommodation:
        raise HTTPException(status_code=404, detail="Accommodation not found")

    # Verificar que el tipo de habitación exista
    result = await db.execute(
        select(RoomTypeTable).where(RoomTypeTable.id == room.type_id)
    )
    room_type = result.scalar_one_or_none()
    if not room_type:
        raise HTTPException(status_code=404, detail="Room type not found")

    # Verificar permisos: solo admin o creador del alojamiento
    if user.role != "admin" and accommodation.created_by != username:
        raise HTTPException(status_code=403, detail="Not authorized to add room")

    # Verificar si ya existe una habitación con el mismo accommodation_id y number
    result = await db.execute(
        select(RoomTable).where(
            RoomTable.accommodation_id == room.accommodation_id,
            RoomTable.number == room.number
        )
    )
    existing_room = result.scalar_one_or_none()
    if existing_room:
        raise HTTPException(
            status_code=409,
            detail=f"Room with number '{room.number}' already exists for accommodation {room.accommodation_id}"
        )

    # Crear la habitación
    db_room = RoomTable(
        accommodation_id=room.accommodation_id,
        type_id=room.type_id,
        number=room.number,
        is_available=room.isAvailable
    )
    db.add(db_room)
    await db.commit()

    # Cargar la relación images para evitar problemas con Pydantic
    result = await db.execute(
        select(RoomTable).where(RoomTable.id == db_room.id).options(selectinload(RoomTable.images))
    )
    db_room = result.scalar_one()
    return Room.model_validate(db_room)

async def upload_images(
        db: AsyncSession,
        request: ImageBase,
        files: List[UploadFile],
        username: str
) -> List[Image]:
    if (request.accommodation_id is None and request.room_id is None) or \
            (request.accommodation_id is not None and request.room_id is not None):
        raise HTTPException(
            status_code=400,
            detail="Exactly one of accommodation_id or room_id must be provided"
        )

    entity = None
    room = None

    if request.accommodation_id:
        result = await db.execute(
            select(AccommodationTable).where(AccommodationTable.id == request.accommodation_id)
        )
        entity = result.scalar_one_or_none()
        if not entity:
            raise HTTPException(status_code=404, detail="Accommodation not found")
        if entity.created_by != username:
            raise HTTPException(status_code=403, detail="Not authorized to upload images")
    else:  # request.room_id
        result = await db.execute(
            select(RoomTable)
            .where(RoomTable.id == request.room_id)
            .options(selectinload(RoomTable.accommodation))
        )
        room = result.scalar_one_or_none()
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        if room.accommodation.created_by != username:
            raise HTTPException(status_code=403, detail="Not authorized to upload images")

    # Usamos STATIC_DIR e IMAGES_DIR desde settings.py
    upload_dir = os.path.join(STATIC_DIR, IMAGES_DIR)
    os.makedirs(upload_dir, exist_ok=True)

    uploaded_images = []
    for file in files:
        file_extension = file.filename.split(".")[-1]
        file_name = f"{uuid.uuid4()}.{file_extension}"
        file_path = os.path.join(upload_dir, file_name)

        with open(file_path, "wb") as f:
            f.write(await file.read())

        db_image = ImageTable(
            url=file_path,
            accommodation_id=request.accommodation_id,
            room_id=request.room_id
        )
        db.add(db_image)
        uploaded_images.append(db_image)

    await db.commit()
    for image in uploaded_images:
        await db.refresh(image)

    return [Image.model_validate(image) for image in uploaded_images]

async def get_available_rooms(
        db: AsyncSession,
        start_date: date,
        end_date: date,
        username: str,
        accommodation_id: int | None = None
) -> List[Room]:
    logger.info(f"Checking available rooms for {username} from {start_date} to {end_date}, accommodation_id={accommodation_id}")

    # Validar fechas
    if start_date >= end_date:
        raise HTTPException(
            status_code=400,
            detail="Start date must be before end date"
        )

    # Verificar usuario y permisos
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    logger.info(f"User role: {user.role}")

    # Obtener todas las habitaciones según permisos
    if user.role == "admin":
        if accommodation_id:
            result = await db.execute(
                select(RoomTable)
                .where(RoomTable.accommodation_id == accommodation_id)
                .options(selectinload(RoomTable.images))
            )
        else:
            result = await db.execute(
                select(RoomTable)
                .options(selectinload(RoomTable.images))
            )
    elif user.role == "user":
        if accommodation_id:
            result = await db.execute(
                select(RoomTable)
                .join(AccommodationTable)
                .where(RoomTable.accommodation_id == accommodation_id)
                .where(AccommodationTable.created_by == username)
                .options(selectinload(RoomTable.images))
            )
        else:
            result = await db.execute(
                select(RoomTable)
                .join(AccommodationTable)
                .where(AccommodationTable.created_by == username)
                .options(selectinload(RoomTable.images))
            )
    else:
        raise HTTPException(status_code=403, detail="Invalid role")

    all_rooms = result.scalars().all()
    logger.info(f"Found {len(all_rooms)} total rooms: {[room.id for room in all_rooms]}")

    if not all_rooms and accommodation_id:
        raise HTTPException(status_code=404, detail="No rooms found for this accommodation")

    # Obtener todas las reservaciones que se superponen con las fechas dadas
    result = await db.execute(
        select(ReservationTable)
        .where(
            (ReservationTable.start_date < end_date) &
            (ReservationTable.end_date > start_date)
        )
    )
    booked_reservations = result.scalars().all()
    logger.info(f"Found {len(booked_reservations)} booked reservations: {[(r.room_id, r.start_date, r.end_date) for r in booked_reservations]}")
    booked_room_ids = {reservation.room_id for reservation in booked_reservations}
    logger.info(f"Booked room IDs: {booked_room_ids}")

    # Filtrar habitaciones disponibles
    available_rooms = [
        room for room in all_rooms
        if room.id not in booked_room_ids
    ]
    logger.info(f"Available rooms: {[room.id for room in available_rooms]}")

    return [Room.model_validate(room) for room in available_rooms]

async def get_booked_rooms(
        db: AsyncSession,
        start_date: date,
        end_date: date,
        username: str,
        accommodation_id: int | None = None
) -> List[Room]:
    # Validar fechas
    if start_date >= end_date:
        raise HTTPException(
            status_code=400,
            detail="Start date must be before end date"
        )

    # Verificar usuario y permisos
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Obtener todas las habitaciones según permisos
    if user.role == "admin":
        if accommodation_id:
            result = await db.execute(
                select(RoomTable)
                .where(RoomTable.accommodation_id == accommodation_id)
                .options(selectinload(RoomTable.images))
            )
        else:
            result = await db.execute(
                select(RoomTable)
                .options(selectinload(RoomTable.images))
            )
    elif user.role == "user":
        if accommodation_id:
            result = await db.execute(
                select(RoomTable)
                .join(AccommodationTable)
                .where(RoomTable.accommodation_id == accommodation_id)
                .where(AccommodationTable.created_by == username)
                .options(selectinload(RoomTable.images))
            )
        else:
            result = await db.execute(
                select(RoomTable)
                .join(AccommodationTable)
                .where(AccommodationTable.created_by == username)
                .options(selectinload(RoomTable.images))
            )
    else:
        raise HTTPException(status_code=403, detail="Invalid role")

    all_rooms = result.scalars().all()

    if not all_rooms and accommodation_id:
        raise HTTPException(status_code=404, detail="No rooms found for this accommodation")

    # Obtener todas las reservaciones que se superponen con las fechas dadas
    result = await db.execute(
        select(ReservationTable)
        .where(
            (ReservationTable.start_date < end_date) &
            (ReservationTable.end_date > start_date)
        )
    )
    booked_reservations = result.scalars().all()
    booked_room_ids = {reservation.room_id for reservation in booked_reservations}

    # Filtrar habitaciones reservadas
    booked_rooms = [
        room for room in all_rooms
        if room.id in booked_room_ids
    ]

    return [Room.model_validate(room) for room in booked_rooms]