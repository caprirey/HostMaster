from fastapi import HTTPException, status, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.models.pydantic_models import (
    RoomType,
    Room,
    RoomBase,
    ImageBase,
    Image,
    RoomUpdate
)
from app.models.sqlalchemy_models import (
    Image as ImageTable,
    Accommodation as AccommodationTable,
    RoomType as RoomTypeTable,
    Room as RoomTable,
    UserTable,
    Reservation as ReservationTable,
)
import os
import uuid
from typing import List, Optional
from datetime import date
from app.config.settings import STATIC_DIR, IMAGES_DIR
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        .options(selectinload(AccommodationTable.users))
    )
    accommodation = result.scalar_one_or_none()
    if not accommodation:
        raise HTTPException(status_code=404, detail="Accommodation not found")

    # Aplicar permisos según el rol
    if user.role == "admin" or user.role == "client":
        pass  # Admin y User pueden ver todas las habitaciones sin restricciones
    elif user.role == "employee":
        # Employee solo puede ver si está relacionado con el alojamiento
        if username not in [u.username for u in accommodation.users]:
            raise HTTPException(status_code=403, detail="Not authorized to view rooms of this accommodation")
    else:
        raise HTTPException(status_code=403, detail="Invalid role")

    # Obtener todas las habitaciones del alojamiento con sus relaciones
    result = await db.execute(
        select(RoomTable)
        .where(RoomTable.accommodation_id == accommodation_id)
        .options(
            selectinload(RoomTable.images),
            selectinload(RoomTable.inventory_items),
            selectinload(RoomTable.room_type),
            selectinload(RoomTable.products)  # Nueva relación
        )
    )
    rooms = result.scalars().all()
    return [Room.model_validate(room) for room in rooms]

async def create_room(db: AsyncSession, room: RoomBase, username: str) -> Room:
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        select(AccommodationTable)
        .where(AccommodationTable.id == room.accommodation_id)
        .options(selectinload(AccommodationTable.users))
    )
    accommodation = result.scalar_one_or_none()
    if not accommodation:
        raise HTTPException(status_code=404, detail="Accommodation not found")

    result = await db.execute(
        select(RoomTypeTable).where(RoomTypeTable.id == room.type_id)
    )
    room_type = result.scalar_one_or_none()
    if not room_type:
        raise HTTPException(status_code=404, detail="Room type not found")

    if user.role != "admin" and username not in [u.username for u in accommodation.users]:
        raise HTTPException(status_code=403, detail="Not authorized to add room")

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

    db_room = RoomTable(
        accommodation_id=room.accommodation_id,
        type_id=room.type_id,
        number=room.number,
        isAvailable=room.isAvailable,
        price=room.price
    )
    db.add(db_room)
    await db.commit()

    result = await db.execute(
        select(RoomTable)
        .where(RoomTable.id == db_room.id)
        .options(
            selectinload(RoomTable.images),
            selectinload(RoomTable.inventory_items),
            selectinload(RoomTable.room_type),
            selectinload(RoomTable.products)  # Cargar la relación products
        )
    )
    db_room = result.scalar_one()
    return Room.model_validate(db_room)

async def update_room(db: AsyncSession, room_id: int, room_update: RoomUpdate, username: str) -> Room:
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        select(RoomTable)
        .where(RoomTable.id == room_id)
        .options(
            selectinload(RoomTable.images),
            selectinload(RoomTable.inventory_items),
            selectinload(RoomTable.room_type),
            selectinload(RoomTable.accommodation).selectinload(AccommodationTable.users)
        )
    )
    db_room = result.scalar_one_or_none()
    if not db_room:
        raise HTTPException(status_code=404, detail="Room not found")

    if user.role != "admin" and username not in [u.username for u in db_room.accommodation.users]:
        raise HTTPException(status_code=403, detail="Not authorized to update this room")

    if room_update.accommodation_id is not None:
        result = await db.execute(
            select(AccommodationTable).where(AccommodationTable.id == room_update.accommodation_id)
        )
        new_accommodation = result.scalar_one_or_none()
        if not new_accommodation:
            raise HTTPException(status_code=404, detail="New accommodation not found")

    if room_update.type_id is not None:
        result = await db.execute(
            select(RoomTypeTable).where(RoomTypeTable.id == room_update.type_id)
        )
        room_type = result.scalar_one_or_none()
        if not room_type:
            raise HTTPException(status_code=404, detail="Room type not found")

    if room_update.accommodation_id is not None or room_update.number is not None:
        check_accommodation_id = room_update.accommodation_id if room_update.accommodation_id is not None else db_room.accommodation_id
        check_number = room_update.number if room_update.number is not None else db_room.number
        result = await db.execute(
            select(RoomTable)
            .where(RoomTable.accommodation_id == check_accommodation_id)
            .where(RoomTable.number == check_number)
            .where(RoomTable.id != room_id)
        )
        existing_room = result.scalar_one_or_none()
        if existing_room:
            raise HTTPException(
                status_code=409,
                detail=f"Room with number '{check_number}' already exists for accommodation {check_accommodation_id}"
            )

    update_data = room_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_room, key, value)

    await db.commit()

    result = await db.execute(
        select(RoomTable)
        .where(RoomTable.id == db_room.id)
        .options(
            selectinload(RoomTable.images),
            selectinload(RoomTable.inventory_items),
            selectinload(RoomTable.room_type),
            selectinload(RoomTable.products)  # Cargar la relación products
        )
    )
    db_room = result.scalar_one()
    return Room.model_validate(db_room)

async def get_all_rooms(db: AsyncSession, username: str) -> List[Room]:
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    query = select(RoomTable).options(
        selectinload(RoomTable.images),
        selectinload(RoomTable.inventory_items),
        selectinload(RoomTable.products)
    )

    if user.role == "employee":
        query = query.join(AccommodationTable).join(AccommodationTable.users).where(UserTable.username == username)

    result = await db.execute(query)
    rooms = result.scalars().all()
    return [Room.model_validate(room) for room in rooms]

async def delete_room(db: AsyncSession, room_id: int, username: str) -> None:
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        select(RoomTable)
        .where(RoomTable.id == room_id)
        .options(
            selectinload(RoomTable.accommodation).selectinload(AccommodationTable.users),
            selectinload(RoomTable.reservations)
        )
    )
    db_room = result.scalar_one_or_none()
    if not db_room:
        raise HTTPException(status_code=404, detail="Room not found")

    if user.role != "admin" and username not in [u.username for u in db_room.accommodation.users]:
        raise HTTPException(status_code=403, detail="Not authorized to delete this room")

    if db_room.reservations:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete room with existing reservations"
        )

    result = await db.execute(
        select(ImageTable).where(ImageTable.room_id == room_id)
    )
    images = result.scalars().all()
    for image in images:
        await db.delete(image)

    await db.delete(db_room)
    await db.commit()

async def get_available_rooms(
        db: AsyncSession,
        start_date: date,
        end_date: date,
        username: str,
        accommodation_id: Optional[int] = None
) -> List[Room]:
    logger.info(f"Checking available rooms for {username} from {start_date} to {end_date}, accommodation_id={accommodation_id}")

    # Validar fechas
    if start_date >= end_date:
        raise HTTPException(status_code=400, detail="Start date must be before end date")

    # Verificar que el usuario exista
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    logger.info(f"User role: {user.role}")

    # Construir la consulta base para habitaciones
    query = select(RoomTable).options(
        selectinload(RoomTable.images),
        selectinload(RoomTable.inventory_items),  # Cargar inventory_items
        selectinload(RoomTable.room_type),  # Cargar room_type
        selectinload(RoomTable.products)  # Cargar products
    )

    # Filtrar por alojamiento si se proporciona
    if accommodation_id:
        query = query.where(RoomTable.accommodation_id == accommodation_id)
        # Verificar que el alojamiento exista
        result = await db.execute(
            select(AccommodationTable)
            .where(AccommodationTable.id == accommodation_id)
            .options(selectinload(AccommodationTable.users))
        )
        accommodation = result.scalar_one_or_none()
        if not accommodation:
            raise HTTPException(status_code=404, detail="Accommodation not found")

    # Aplicar permisos según el rol
    if user.role == "admin" or user.role == "client":
        pass  # Admin y User ven todas las habitaciones
    elif user.role == "employee":
        if accommodation_id:
            # Employee solo puede ver si está relacionado con el alojamiento
            if username not in [u.username for u in accommodation.users]:
                raise HTTPException(status_code=403, detail="Not authorized to view rooms of this accommodation")
        else:
            # Si no hay accommodation_id, filtrar por alojamientos relacionados
            query = query.join(AccommodationTable).join(AccommodationTable.users).where(UserTable.username == username)
    else:
        raise HTTPException(status_code=403, detail="Invalid role")

    # Obtener todas las habitaciones (antes de filtrar disponibilidad)
    result = await db.execute(query)
    all_rooms = result.scalars().all()
    logger.info(f"Found {len(all_rooms)} total rooms: {[room.id for room in all_rooms]}")

    if not all_rooms and accommodation_id:
        raise HTTPException(status_code=404, detail="No rooms found for this accommodation")

    # Obtener reservas que se solapen con el período
    result = await db.execute(
        select(ReservationTable)
        .where(
            (ReservationTable.start_date < end_date) &
            (ReservationTable.end_date > start_date) &
            (ReservationTable.status == "confirmed")  # Solo reservas confirmadas
        )
    )
    booked_reservations = result.scalars().all()
    logger.info(f"Found {len(booked_reservations)} booked reservations: {[(r.room_id, r.start_date, r.end_date) for r in booked_reservations]}")
    booked_room_ids = {reservation.room_id for reservation in booked_reservations}
    logger.info(f"Booked room IDs: {booked_room_ids}")

    # Filtrar habitaciones disponibles
    available_rooms = [
        room for room in all_rooms
        if room.id not in booked_room_ids and room.isAvailable
    ]
    logger.info(f"Available rooms: {[room.id for room in available_rooms]}")

    return [Room.model_validate(room) for room in available_rooms]

async def get_booked_rooms(
        db: AsyncSession,
        start_date: date,
        end_date: date,
        username: str,
        accommodation_id: Optional[int] = None
) -> List[Room]:
    logger.info(f"Checking booked rooms for {username} from {start_date} to {end_date}, accommodation_id={accommodation_id}")

    # Validar fechas
    if start_date >= end_date:
        raise HTTPException(status_code=400, detail="Start date must be before end date")

    # Verificar que el usuario exista
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    logger.info(f"User role: {user.role}")

    # Construir la consulta base para habitaciones
    query = select(RoomTable).options(
        selectinload(RoomTable.images),
        selectinload(RoomTable.inventory_items),  # Cargar inventory_items
        selectinload(RoomTable.room_type),  # Cargar room_type
        selectinload(RoomTable.products)  # Cargar products
    )

    # Filtrar por alojamiento si se proporciona
    if accommodation_id:
        query = query.where(RoomTable.accommodation_id == accommodation_id)
        # Verificar que el alojamiento exista
        result = await db.execute(
            select(AccommodationTable)
            .where(AccommodationTable.id == accommodation_id)
            .options(selectinload(AccommodationTable.users))
        )
        accommodation = result.scalar_one_or_none()
        if not accommodation:
            raise HTTPException(status_code=404, detail="Accommodation not found")

    # Aplicar permisos según el rol
    if user.role == "admin" or user.role == "client":
        pass  # Admin y User ven todas las habitaciones reservadas
    elif user.role == "employee":
        if accommodation_id:
            # Employee solo puede ver si está relacionado con el alojamiento
            if username not in [u.username for u in accommodation.users]:
                raise HTTPException(status_code=403, detail="Not authorized to view rooms of this accommodation")
        else:
            # Si no hay accommodation_id, filtrar por alojamientos relacionados
            query = query.join(AccommodationTable).join(AccommodationTable.users).where(UserTable.username == username)
    else:
        raise HTTPException(status_code=403, detail="Invalid role")

    # Obtener todas las habitaciones (antes de filtrar reservas)
    result = await db.execute(query)
    all_rooms = result.scalars().all()
    logger.info(f"Found {len(all_rooms)} total rooms: {[room.id for room in all_rooms]}")

    if not all_rooms and accommodation_id:
        raise HTTPException(status_code=404, detail="No rooms found for this accommodation")

    # Obtener reservas confirmadas que se solapen con el período
    result = await db.execute(
        select(ReservationTable)
        .where(
            (ReservationTable.start_date < end_date) &
            (ReservationTable.end_date > start_date) &
            (ReservationTable.status == "confirmed")  # Solo reservas confirmadas
        )
    )
    booked_reservations = result.scalars().all()
    logger.info(f"Found {len(booked_reservations)} booked reservations: {[(r.room_id, r.start_date, r.end_date) for r in booked_reservations]}")
    booked_room_ids = {reservation.room_id for reservation in booked_reservations}
    logger.info(f"Booked room IDs: {booked_room_ids}")

    # Filtrar habitaciones reservadas
    booked_rooms = [
        room for room in all_rooms
        if room.id in booked_room_ids
    ]
    logger.info(f"Booked rooms: {[room.id for room in booked_rooms]}")

    return [Room.model_validate(room) for room in booked_rooms]

async def get_room_type(db: AsyncSession, room_type_id: int) -> RoomType:
    result = await db.execute(
        select(RoomTypeTable).where(RoomTypeTable.id == room_type_id)
    )
    db_room_type = result.scalar_one_or_none()
    if not db_room_type:
        raise HTTPException(status_code=404, detail="Room type not found")
    return RoomType.model_validate(db_room_type)

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
            select(AccommodationTable)
            .where(AccommodationTable.id == request.accommodation_id)
            .options(selectinload(AccommodationTable.users))
        )
        entity = result.scalar_one_or_none()
        if not entity:
            raise HTTPException(status_code=404, detail="Accommodation not found")
        if username not in [u.username for u in entity.users]:
            raise HTTPException(status_code=403, detail="Not authorized to upload images")
    else:  # request.room_id
        result = await db.execute(
            select(RoomTable)
            .where(RoomTable.id == request.room_id)
            .options(selectinload(RoomTable.accommodation).selectinload(AccommodationTable.users))
        )
        room = result.scalar_one_or_none()
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        if username not in [u.username for u in room.accommodation.users]:
            raise HTTPException(status_code=403, detail="Not authorized to upload images")

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

async def get_rooms_by_accommodation(db: AsyncSession, accommodation_id: int, username: str) -> List[Room]:
    """
    Retrieve all rooms for a specific accommodation based on user role permissions.

    Args:
        db (AsyncSession): Database session
        accommodation_id (int): ID of the accommodation to fetch rooms from
        username (str): Username of the authenticated user

    Returns:
        List[Room]: List of rooms associated with the accommodation

    Raises:
        HTTPException: 404 if user or accommodation not found, 403 if not authorized
    """
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        select(AccommodationTable)
        .where(AccommodationTable.id == accommodation_id)
        .options(selectinload(AccommodationTable.users))
    )
    accommodation = result.scalar_one_or_none()
    if not accommodation:
        raise HTTPException(status_code=404, detail="Accommodation not found")

    if user.role == "employee":
        if username not in [u.username for u in accommodation.users]:
            raise HTTPException(status_code=403, detail="Not authorized to view rooms of this accommodation")

    result = await db.execute(
        select(RoomTable)
        .where(RoomTable.accommodation_id == accommodation_id)
        .options(
            selectinload(RoomTable.images),
            selectinload(RoomTable.inventory_items),
            selectinload(RoomTable.room_type),
            selectinload(RoomTable.products)  # Cargar la relación products
        )
    )
    rooms = result.scalars().all()

    return [Room.model_validate(room) for room in rooms]


async def get_room_by_id(db: AsyncSession, room_id: int, username: str) -> Room:
    """
    Retrieve a specific room by its ID based on user role permissions.

    Args:
        db (AsyncSession): Database session
        room_id (int): ID of the room to fetch
        username (str): Username of the authenticated user

    Returns:
        Room: The requested room with its associated data

    Raises:
        HTTPException: 404 if user or room not found, 403 if not authorized
    """
    # Verificar que el usuario exista
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Obtener la habitación con sus relaciones y el alojamiento asociado
    result = await db.execute(
        select(RoomTable)
        .where(RoomTable.id == room_id)
        .options(
            selectinload(RoomTable.images),
            selectinload(RoomTable.inventory_items),
            selectinload(RoomTable.room_type),
            selectinload(RoomTable.products),
            selectinload(RoomTable.accommodation).selectinload(AccommodationTable.users)
        )
    )
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    # Aplicar permisos según el rol
    if user.role == "admin" or user.role == "client":
        pass  # Admin y Client pueden ver cualquier habitación
    elif user.role == "employee":
        # Employee solo puede ver si está relacionado con el alojamiento
        if username not in [u.username for u in room.accommodation.users]:
            raise HTTPException(status_code=403, detail="Not authorized to view this room")
    else:
        raise HTTPException(status_code=403, detail="Invalid role")

    return Room.model_validate(room)