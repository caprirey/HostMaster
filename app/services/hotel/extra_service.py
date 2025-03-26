# app/services/hotel/extra_service.py
from typing import List

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.sqlalchemy_models import UserTable, ExtraService as ExtraServiceTable, \
    Reservation, Room, Accommodation  # Alias para claridad
from app.models.pydantic_models import ExtraService, ExtraServiceCreate, ExtraServiceUpdate
from sqlalchemy.orm import selectinload

async def create_extra_service(db: AsyncSession, extra_service_data: ExtraServiceCreate, username: str) -> ExtraService:
    # Verificar que el usuario exista
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Validar permisos
    if user.role != "admin":
        # Si no es admin, verificar si el usuario es creador de al menos un alojamiento
        result = await db.execute(
            select(Accommodation).where(Accommodation.created_by == username).limit(1)
        )
        has_accommodation = result.scalar_one_or_none()
        if not has_accommodation:
            raise HTTPException(
                status_code=403,
                detail="Only admin or accommodation creators can create extra services"
            )

    # Crear el servicio extra
    db_extra_service = ExtraServiceTable(
        name=extra_service_data.name,
        description=extra_service_data.description,
        price=extra_service_data.price
    )
    db.add(db_extra_service)
    await db.commit()
    await db.refresh(db_extra_service)  # Refrescar para obtener el ID generado

    return ExtraService.model_validate(db_extra_service)


async def update_extra_service(
        db: AsyncSession,
        extra_service_id: int,
        extra_service_data: ExtraServiceUpdate,
        username: str
) -> ExtraService:
    # Verificar que el usuario exista
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Validar rol: solo admin puede actualizar servicios extras
    if user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only users with 'admin' role can update extra services"
        )

    # Buscar el servicio extra existente
    result = await db.execute(
        select(ExtraServiceTable).where(ExtraServiceTable.id == extra_service_id)
    )
    db_extra_service = result.scalar_one_or_none()
    if not db_extra_service:
        raise HTTPException(status_code=404, detail="Extra service not found")

    # Actualizar los campos proporcionados
    update_data = extra_service_data.model_dump(exclude_unset=True)  # Solo campos enviados
    for key, value in update_data.items():
        setattr(db_extra_service, key, value)

    await db.commit()
    await db.refresh(db_extra_service)  # Refrescar para obtener los datos actualizados

    # Convertir a modelo Pydantic para la respuesta
    return ExtraService.model_validate(db_extra_service)


async def delete_extra_service(db: AsyncSession, extra_service_id: int, username: str) -> None:
    # Verificar que el usuario exista
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Buscar el servicio extra con sus reservas
    result = await db.execute(
        select(ExtraServiceTable)
        .where(ExtraServiceTable.id == extra_service_id)
        .options(selectinload(ExtraServiceTable.reservations).selectinload(Reservation.room).selectinload(Room.accommodation))
    )
    db_extra_service = result.scalar_one_or_none()
    if not db_extra_service:
        raise HTTPException(status_code=404, detail="Extra service not found")

    # Validar permisos
    if user.role != "admin":
        # Si no es admin, verificar si el usuario es el creador de algún alojamiento asociado
        allowed = False
        for reservation in db_extra_service.reservations:
            if reservation.room.accommodation.created_by == username:
                allowed = True
                break
        if not allowed:
            raise HTTPException(
                status_code=403,
                detail="Only admin or the accommodation creator associated with this service can delete it"
            )

    # Opcional: Impedir eliminación si está en uso
    # if db_extra_service.reservations:
    #     raise HTTPException(
    #         status_code=400,
    #         detail="Cannot delete extra service with associated reservations"
    #     )

    # Eliminar el servicio extra
    await db.delete(db_extra_service)
    await db.commit()


async def get_extra_service(db: AsyncSession, extra_service_id: int, username: str) -> ExtraService:
    # Verificar que el usuario exista
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Buscar el servicio extra con sus reservas
    result = await db.execute(
        select(ExtraServiceTable)
        .where(ExtraServiceTable.id == extra_service_id)
        .options(selectinload(ExtraServiceTable.reservations).selectinload(Reservation.room).selectinload(Room.accommodation))
    )
    db_extra_service = result.scalar_one_or_none()
    if not db_extra_service:
        raise HTTPException(status_code=404, detail="Extra service not found")

    # Si es admin, permitir acceso
    if user.role == "admin":
        return ExtraService.model_validate(db_extra_service)

    # Si no es admin, verificar si está asociado a un alojamiento del usuario
    for reservation in db_extra_service.reservations:
        if reservation.room.accommodation.created_by == username:
            return ExtraService.model_validate(db_extra_service)

    # Si no se encuentra ninguna coincidencia, denegar acceso
    raise HTTPException(
        status_code=403,
        detail="Only admin or the accommodation creator associated with this service can view it"
    )

# app/services/hotel/extra_service.py
async def get_all_extra_services(db: AsyncSession, username: str) -> List[ExtraService]:
    # Verificar que el usuario exista
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Si es admin, devolver todos los servicios extras
    if user.role == "admin":
        result = await db.execute(
            select(ExtraServiceTable)
            .options(selectinload(ExtraServiceTable.reservations).selectinload(Reservation.room).selectinload(Room.accommodation))
        )
        db_extra_services = result.scalars().all()
        return [ExtraService.model_validate(service) for service in db_extra_services]

    # Si no es admin, filtrar por alojamientos del usuario
    result = await db.execute(
        select(ExtraServiceTable)
        .join(ExtraServiceTable.reservations)
        .join(Reservation.room)
        .join(Room.accommodation)
        .where(Accommodation.created_by == username)
        .options(selectinload(ExtraServiceTable.reservations).selectinload(Reservation.room).selectinload(Room.accommodation))
    )
    db_extra_services = result.scalars().all()
    return [ExtraService.model_validate(service) for service in db_extra_services]