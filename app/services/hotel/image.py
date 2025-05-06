import os
import uuid
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.pydantic_models import Image, ImageBase
from app.models.sqlalchemy_models import (
    Image as ImageTable, Accommodation as AccommodationTable, Room as RoomTable, UserTable
)
from app.config.settings import BASE_URL, STATIC_DIR, IMAGES_DIR
from sqlalchemy.orm import selectinload

STATIC_PATH = os.path.join(STATIC_DIR, IMAGES_DIR)

async def create_image(db: AsyncSession, image_file: UploadFile, image_data: ImageBase, username: str) -> Image:
    # Validar que exactamente uno de accommodation_id o room_id esté presente
    if (image_data.accommodation_id is not None and image_data.room_id is not None) or \
            (image_data.accommodation_id is None and image_data.room_id is None):
        raise HTTPException(
            status_code=400,
            detail="Exactly one of accommodation_id or room_id must be provided, but not both or neither."
        )

    # Verificar permisos
    if image_data.accommodation_id:
        result = await db.execute(
            select(AccommodationTable).where(AccommodationTable.id == image_data.accommodation_id)
        )
        accommodation = result.scalar_one_or_none()
        if not accommodation or (accommodation.created_by != username and username != "admin"):
            raise HTTPException(status_code=403, detail="No permission to add image to this accommodation")

    if image_data.room_id:
        result = await db.execute(
            select(RoomTable).join(AccommodationTable).where(RoomTable.id == image_data.room_id)
        )
        room = result.scalar_one_or_none()
        if not room or (room.accommodation.created_by != username and username != "admin"):
            raise HTTPException(status_code=403, detail="No permission to add image to this room")

    # Generar un nombre único para el archivo
    file_extension = image_file.filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join(STATIC_PATH, filename)

    # Guardar la imagen
    with open(file_path, "wb") as f:
        f.write(await image_file.read())

    # Generar la URL
    url = f"{BASE_URL}/static/{IMAGES_DIR}/{filename}"

    # Guardar en la base de datos
    image = ImageTable(
        url=url,
        accommodation_id=image_data.accommodation_id,
        room_id=image_data.room_id
    )
    db.add(image)
    await db.commit()
    await db.refresh(image)
    return Image.model_validate(image)

async def get_images(db: AsyncSession, username: str, accommodation_id: int = None, room_id: int = None) -> list[Image]:
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    query = select(ImageTable)
    if accommodation_id:
        query = query.where(ImageTable.accommodation_id == accommodation_id)
        if user.role == "client":
            result = await db.execute(
                select(AccommodationTable).where(
                    AccommodationTable.id == accommodation_id,
                    AccommodationTable.created_by == username
                )
            )
            if not result.scalar_one_or_none():
                return []
    if room_id:
        query = query.where(ImageTable.room_id == room_id)
        if user.role == "client":
            result = await db.execute(
                select(RoomTable).join(AccommodationTable).where(
                    RoomTable.id == room_id,
                    AccommodationTable.created_by == username
                )
            )
            if not result.scalar_one_or_none():
                return []

    if not accommodation_id and not room_id and user.role == "client":
        result = await db.execute(
            select(AccommodationTable).where(AccommodationTable.created_by == username)
        )
        user_accommodations = result.scalars().all()
        if not user_accommodations:
            return []
        query = query.where(
            ImageTable.accommodation_id.in_([a.id for a in user_accommodations]) |
            ImageTable.room_id.in_([r.id for a in user_accommodations for r in a.rooms])
        )

    result = await db.execute(query)
    images = result.scalars().all()
    return [Image.model_validate(image) for image in images]


async def delete_images(
        db: AsyncSession,
        accommodation_id: int | None = None,
        room_id: int | None = None,
        username: str = None
) -> None:
    # Verificar que se proporcione al menos un ID
    if accommodation_id is None and room_id is None:
        raise HTTPException(
            status_code=400,
            detail="Must provide either accommodation_id or room_id"
        )

    # Verificar que el usuario exista
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Caso 1: Eliminar imágenes de un alojamiento
    if accommodation_id is not None:
        result = await db.execute(
            select(AccommodationTable)
            .where(AccommodationTable.id == accommodation_id)
            .options(selectinload(AccommodationTable.images))
        )
        db_accommodation = result.scalar_one_or_none()
        if not db_accommodation:
            raise HTTPException(status_code=404, detail="Accommodation not found")

        # Verificar permisos: solo el creador o un admin puede eliminar imágenes
        if user.role != "admin" and db_accommodation.created_by != username:
            raise HTTPException(status_code=403, detail="Not authorized to delete images for this accommodation")

        # Eliminar imágenes asociadas al alojamiento
        result = await db.execute(
            select(ImageTable).where(ImageTable.accommodation_id == accommodation_id)
        )
        images = result.scalars().all()
        for image in images:
            await db.delete(image)

    # Caso 2: Eliminar imágenes de una habitación
    if room_id is not None:
        result = await db.execute(
            select(RoomTable)
            .where(RoomTable.id == room_id)
            .options(selectinload(RoomTable.accommodation))
        )
        db_room = result.scalar_one_or_none()
        if not db_room:
            raise HTTPException(status_code=404, detail="Room not found")

        # Verificar permisos: solo el creador del alojamiento o un admin puede eliminar imágenes
        if user.role != "admin" and db_room.accommodation.created_by != username:
            raise HTTPException(status_code=403, detail="Not authorized to delete images for this room")

        # Eliminar imágenes asociadas a la habitación
        result = await db.execute(
            select(ImageTable).where(ImageTable.room_id == room_id)
        )
        images = result.scalars().all()
        for image in images:
            await db.delete(image)

    # Confirmar cambios
    await db.commit()