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
    Reservation,
    # Añadido para get_available_rooms
    AccommodationUpdate,
    RoomUpdate
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
        created_by=username,  # El creador es el usuario autenticado
        address=accommodation.address,
        information=accommodation.information
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

async def update_accommodation(
        db: AsyncSession,
        accommodation_id: int,
        accommodation_update: AccommodationUpdate,
        username: str
) -> Accommodation:
    # Verificar que el usuario exista
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Buscar el alojamiento existente
    result = await db.execute(
        select(AccommodationTable)
        .where(AccommodationTable.id == accommodation_id)
        .options(selectinload(AccommodationTable.images))
    )
    db_accommodation = result.scalar_one_or_none()
    if not db_accommodation:
        raise HTTPException(status_code=404, detail="Accommodation not found")

    # Verificar permisos: solo admin o creador del alojamiento
    if user.role != "admin" and db_accommodation.created_by != username:
        raise HTTPException(status_code=403, detail="Not authorized to update this accommodation")

    # Verificar que la ciudad exista si se proporciona city_id
    if accommodation_update.city_id is not None:
        result = await db.execute(
            select(CityTable).where(CityTable.id == accommodation_update.city_id)
        )
        city = result.scalar_one_or_none()
        if not city:
            raise HTTPException(status_code=404, detail="City not found")

    # Actualizar los campos proporcionados
    update_data = accommodation_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_accommodation, key, value)

    await db.commit()
    await db.refresh(db_accommodation)
    return Accommodation.model_validate(db_accommodation)


async def get_rooms(db: AsyncSession, username: str, accommodation_id: int) -> List[Room]:
    # Verificar que el usuario exista
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verificar que el alojamiento exista
    result = await db.execute(
        select(AccommodationTable)
        .where(AccommodationTable.id == accommodation_id)
    )
    accommodation = result.scalar_one_or_none()
    if not accommodation:
        raise HTTPException(status_code=404, detail="Accommodation not found")

    # Verificar permisos según el rol del usuario
    if user.role == "admin":
        pass
    elif user.role == "user":
        if accommodation.created_by != username:
            raise HTTPException(status_code=403, detail="Not authorized to view rooms")
    else:
        raise HTTPException(status_code=403, detail="Invalid role")

    # Consultar habitaciones con todas las relaciones relevantes
    result = await db.execute(
        select(RoomTable)
        .where(RoomTable.accommodation_id == accommodation_id)
        .options(
            selectinload(RoomTable.images),           # Cargar relación images
            selectinload(RoomTable.inventory_items),  # Cargar relación inventory_items
            selectinload(RoomTable.room_type)         # Cargar relación room_type
        )
    )
    rooms = result.scalars().all()

    # Convertir a modelos Pydantic
    return [Room.model_validate(room) for room in rooms]

async def create_room_type(
        db: AsyncSession,
        room_type: RoomTypeBase,
        username: str
) -> RoomType:
    # Verificar que el usuario exista
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verificar permisos: solo admin puede crear tipos de habitación
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create room types")

    # Crear el tipo de habitación
    db_room_type = RoomTypeTable(**room_type.model_dump())
    db.add(db_room_type)
    await db.commit()
    await db.refresh(db_room_type)
    return RoomType.model_validate(db_room_type)

async def get_room_types(
        db: AsyncSession,
        username: str
) -> List[RoomType]:
    # Verificar que el usuario exista (autenticación básica)
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Construir la consulta base
    query = select(RoomTypeTable)

    # Filtrar por accommodation_id si se proporciona
    # if accommodation_id:
    #    query = query.where(RoomTypeTable.accommodation_id == accommodation_id)

    # Ejecutar la consulta
    result = await db.execute(query)
    room_types = result.scalars().all()

    # if not room_types and accommodation_id:
    #    raise HTTPException(status_code=404, detail="No room types found for this accommodation")

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
        is_available=room.isAvailable,
        price=room.price
    )
    db.add(db_room)
    await db.commit()

    # Cargar todas las relaciones relevantes para evitar problemas con Pydantic
    result = await db.execute(
        select(RoomTable)
        .where(RoomTable.id == db_room.id)
        .options(
            selectinload(RoomTable.images),           # Cargar relación images
            selectinload(RoomTable.inventory_items),  # Cargar relación inventory_items
            selectinload(RoomTable.room_type)         # Cargar relación room_type
        )
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


async def get_room_type(
        db: AsyncSession,
        room_type_id: int
) -> RoomType:
    # Buscar el RoomType por id
    result = await db.execute(
        select(RoomTypeTable).where(RoomTypeTable.id == room_type_id)
    )
    db_room_type = result.scalar_one_or_none()
    if not db_room_type:
        raise HTTPException(status_code=404, detail="Room type not found")

    return RoomType.model_validate(db_room_type)


async def update_room(
        db: AsyncSession,
        room_id: int,
        room_update: RoomUpdate,
        username: str
) -> Room:
    # Verificar que el usuario exista
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Buscar la habitación existente con relaciones iniciales
    result = await db.execute(
        select(RoomTable)
        .where(RoomTable.id == room_id)
        .options(
            selectinload(RoomTable.images),           # Cargar relación images
            selectinload(RoomTable.inventory_items),  # Cargar relación inventory_items
            selectinload(RoomTable.room_type)         # Cargar relación room_type
        )
    )
    db_room = result.scalar_one_or_none()
    if not db_room:
        raise HTTPException(status_code=404, detail="Room not found")

    # Verificar permisos: solo admin o creador del alojamiento
    result = await db.execute(
        select(AccommodationTable).where(AccommodationTable.id == db_room.accommodation_id)
    )
    accommodation = result.scalar_one_or_none()
    if not accommodation:
        raise HTTPException(status_code=404, detail="Accommodation not found")
    if user.role != "admin" and accommodation.created_by != username:
        raise HTTPException(status_code=403, detail="Not authorized to update this room")

    # Verificar que el accommodation_id exista si se proporciona
    if room_update.accommodation_id is not None:
        result = await db.execute(
            select(AccommodationTable).where(AccommodationTable.id == room_update.accommodation_id)
        )
        new_accommodation = result.scalar_one_or_none()
        if not new_accommodation:
            raise HTTPException(status_code=404, detail="New accommodation not found")

    # Verificar que el type_id exista si se proporciona
    if room_update.type_id is not None:
        result = await db.execute(
            select(RoomTypeTable).where(RoomTypeTable.id == room_update.type_id)
        )
        room_type = result.scalar_one_or_none()
        if not room_type:
            raise HTTPException(status_code=404, detail="Room type not found")

    # Verificar unicidad de accommodation_id y number si se actualizan
    if room_update.accommodation_id is not None or room_update.number is not None:
        check_accommodation_id = room_update.accommodation_id if room_update.accommodation_id is not None else db_room.accommodation_id
        check_number = room_update.number if room_update.number is not None else db_room.number
        result = await db.execute(
            select(RoomTable)
            .where(RoomTable.accommodation_id == check_accommodation_id)
            .where(RoomTable.number == check_number)
            .where(RoomTable.id != room_id)  # Excluir la habitación actual
        )
        existing_room = result.scalar_one_or_none()
        if existing_room:
            raise HTTPException(
                status_code=409,
                detail=f"Room with number '{check_number}' already exists for accommodation {check_accommodation_id}"
            )

    # Actualizar los campos proporcionados
    update_data = room_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_room, key, value)

    await db.commit()

    # Refrescar y cargar todas las relaciones relevantes
    result = await db.execute(
        select(RoomTable)
        .where(RoomTable.id == db_room.id)
        .options(
            selectinload(RoomTable.images),           # Cargar relación images
            selectinload(RoomTable.inventory_items),  # Cargar relación inventory_items
            selectinload(RoomTable.room_type)         # Cargar relación room_type
        )
    )
    db_room = result.scalar_one()
    return Room.model_validate(db_room)

async def get_all_rooms(
        db: AsyncSession,
        username: str
) -> List[Room]:
    # Verificar que el usuario exista
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Construir la consulta de habitaciones
    query = select(RoomTable).options(
        selectinload(RoomTable.images),           # Cargar relación images
        selectinload(RoomTable.inventory_items)   # Cargar relación inventory_items
    )

    # Filtrar según el rol del usuario
    if user.role != "admin":
        # Solo habitaciones de alojamientos creados por el usuario
        query = query.join(AccommodationTable).where(AccommodationTable.created_by == username)

    # Ejecutar la consulta
    result = await db.execute(query)
    rooms = result.scalars().all()

    # Convertir a modelos Pydantic
    return [Room.model_validate(room) for room in rooms]


async def delete_room(db: AsyncSession, room_id: int, username: str) -> None:
    # Verificar que el usuario exista
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Buscar la habitación con su alojamiento y reservas
    result = await db.execute(
        select(RoomTable)
        .where(RoomTable.id == room_id)
        .options(selectinload(RoomTable.accommodation), selectinload(RoomTable.reservations))
    )
    db_room = result.scalar_one_or_none()
    if not db_room:
        raise HTTPException(status_code=404, detail="Room not found")

    # Verificar permisos: solo el creador del alojamiento o un admin puede eliminar
    if user.role != "admin" and db_room.accommodation.created_by != username:
        raise HTTPException(status_code=403, detail="Not authorized to delete this room")

    # Verificar si hay reservas asociadas
    if db_room.reservations:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete room with existing reservations"
        )

    # Eliminar imágenes asociadas (si las hay)
    result = await db.execute(
        select(ImageTable).where(ImageTable.room_id == room_id)
    )
    images = result.scalars().all()
    for image in images:
        await db.delete(image)

    # Eliminar la habitación
    await db.delete(db_room)
    await db.commit()

async def delete_accommodation(db: AsyncSession, accommodation_id: int, username: str) -> None:
    # Verificar que el usuario exista
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Buscar el alojamiento con sus habitaciones e imágenes
    result = await db.execute(
        select(AccommodationTable)
        .where(AccommodationTable.id == accommodation_id)
        .options(selectinload(AccommodationTable.rooms), selectinload(AccommodationTable.images))
    )
    db_accommodation = result.scalar_one_or_none()
    if not db_accommodation:
        raise HTTPException(status_code=404, detail="Accommodation not found")

    # Verificar permisos: solo el creador o un admin puede eliminar
    if user.role != "admin" and db_accommodation.created_by != username:
        raise HTTPException(status_code=403, detail="Not authorized to delete this accommodation")

    # Verificar si hay habitaciones asociadas
    if db_accommodation.rooms:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete accommodation with associated rooms"
        )

    # Eliminar imágenes asociadas al alojamiento
    for image in db_accommodation.images:
        await db.delete(image)

    # Eliminar el alojamiento
    await db.delete(db_accommodation)
    await db.commit()