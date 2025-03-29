from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from app.models.pydantic_models import RoomType, RoomTypeBase
from app.models.sqlalchemy_models import RoomType as RoomTypeTable, UserTable
from sqlalchemy.orm import selectinload

async def create_room_type(db: AsyncSession, room_type_data: RoomTypeBase, current_user: UserTable) -> RoomType:
    """
    Crea un nuevo tipo de habitación. Solo administradores pueden realizar esta acción.
    """
    # Verificar que el usuario sea administrador
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only administrators can create room types")

    # Crear el tipo de habitación
    db_room_type = RoomTypeTable(**room_type_data.model_dump())
    db.add(db_room_type)
    await db.commit()
    await db.refresh(db_room_type)
    return RoomType.model_validate(db_room_type)

async def update_room_type(db: AsyncSession, room_type_id: int, room_type_update: RoomTypeBase, current_user: UserTable) -> RoomType:
    """
    Actualiza un tipo de habitación existente. Solo administradores pueden realizar esta acción.
    """
    # Verificar que el usuario sea administrador
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only administrators can update room types")

    # Buscar el tipo de habitación
    result = await db.execute(select(RoomTypeTable).where(RoomTypeTable.id == room_type_id))
    db_room_type = result.scalar_one_or_none()
    if not db_room_type:
        raise HTTPException(status_code=404, detail="Room type not found")

    # Actualizar los campos proporcionados
    update_data = room_type_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_room_type, key, value)

    await db.commit()
    await db.refresh(db_room_type)
    return RoomType.model_validate(db_room_type)

async def delete_room_type(db: AsyncSession, room_type_id: int, current_user: UserTable) -> None:
    """
    Elimina un tipo de habitación. Solo administradores pueden realizar esta acción.
    Valida que no haya asociaciones en otras tablas (ej. rooms) antes de eliminar.
    """
    # Verificar que el usuario sea administrador
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only administrators can delete room types")

    # Buscar el tipo de habitación con sus relaciones cargadas
    result = await db.execute(
        select(RoomTypeTable)
        .where(RoomTypeTable.id == room_type_id)
        .options(selectinload(RoomTypeTable.rooms))  # Cargar la relación rooms
    )
    db_room_type = result.scalar_one_or_none()
    if not db_room_type:
        raise HTTPException(status_code=404, detail="Room type not found")

    # Validar asociaciones con habitaciones (rooms)
    if db_room_type.rooms:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete room type '{db_room_type.name}' because it is associated with {len(db_room_type.rooms)} room(s)"
        )

    # Si no hay asociaciones, proceder con la eliminación
    await db.delete(db_room_type)
    await db.commit()

async def get_room_types(db: AsyncSession, current_user: UserTable) -> List[RoomType]:
    """
    Obtiene todos los tipos de habitación. Accesible para cualquier usuario autenticado.
    """
    result = await db.execute(select(RoomTypeTable))
    room_types = result.scalars().all()
    return [RoomType.model_validate(room_type) for room_type in room_types]

async def get_room_type(db: AsyncSession, room_type_id: int, current_user: UserTable) -> RoomType:
    """
    Obtiene un tipo de habitación específico por ID. Accesible para cualquier usuario autenticado.
    """
    result = await db.execute(select(RoomTypeTable).where(RoomTypeTable.id == room_type_id))
    db_room_type = result.scalar_one_or_none()
    if not db_room_type:
        raise HTTPException(status_code=404, detail="Room type not found")
    return RoomType.model_validate(db_room_type)