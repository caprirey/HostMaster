from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.models.pydantic_models import (
    Accommodation,
    AccommodationBase,
    RoomType,
    RoomTypeBase,
    Room,
    RoomBase
)
from app.models.sqlalchemy_models import (
    Accommodation as AccommodationTable,
    RoomType as RoomTypeTable,
    Room as RoomTable,
    UserTable  # Importamos UserTable directamente, sin alias 'as User'
)

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
        db: AsyncSession, accommodation: AccommodationBase, username: str
) -> Accommodation:
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db_accommodation = AccommodationTable(**accommodation.model_dump(), created_by=username)
    db.add(db_accommodation)
    await db.commit()
    await db.refresh(db_accommodation)
    return Accommodation.model_validate(db_accommodation)

async def get_rooms(db: AsyncSession, username: str, accommodation_id: int) -> list[Room]:
    # Verificar el rol del usuario
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verificar la existencia del alojamiento
    result = await db.execute(
        select(AccommodationTable)
        .where(AccommodationTable.id == accommodation_id)
    )
    accommodation = result.scalar_one_or_none()
    if not accommodation:
        raise HTTPException(status_code=404, detail="Accommodation not found")

    # Validar permisos según el rol
    if user.role == "admin":
        # Los administradores pueden ver todas las habitaciones
        pass
    elif user.role == "user":
        # Los usuarios solo pueden ver habitaciones de alojamientos que crearon
        if accommodation.created_by != username:
            raise HTTPException(status_code=403, detail="Not authorized to view rooms")
    else:
        raise HTTPException(status_code=403, detail="Invalid role")

    # Consultar las habitaciones con imágenes cargadas ansiosamente
    result = await db.execute(
        select(RoomTable)
        .where(RoomTable.accommodation_id == accommodation_id)
        .options(selectinload(RoomTable.images))  # Cargar imágenes ansiosamente
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

async def create_room(
        db: AsyncSession, room: RoomBase, accommodation_id: int, room_type_id: int, username: str
) -> Room:
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

    result = await db.execute(
        select(RoomTypeTable).where(RoomTypeTable.id == room_type_id)
    )
    room_type = result.scalar_one_or_none()
    if not room_type or room_type.accommodation_id != accommodation_id:
        raise HTTPException(status_code=404, detail="Room type not found or mismatched")

    if user.role != "admin" and accommodation.created_by != username:
        raise HTTPException(status_code=403, detail="Not authorized to add room")

    db_room = RoomTable(
        **room.model_dump(),
        accommodation_id=accommodation_id,
        room_type_id=room_type_id
    )
    db.add(db_room)
    await db.commit()
    await db.refresh(db_room)
    return Room.model_validate(db_room)