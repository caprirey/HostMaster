from typing import List

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.sqlalchemy_models import UserTable as User, ExtraService, \
    Reservation, Room, Accommodation, user_accommodation
from app.models.pydantic_models import ExtraService as ExtraServicePydantic, ExtraServiceCreate, ExtraServiceUpdate
from sqlalchemy.orm import selectinload

async def create_extra_service(db: AsyncSession, extra_service_data: ExtraServiceCreate, username: str) -> ExtraServicePydantic:
    # Verificar que el usuario exista
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Validar permisos
    if user.role != "admin":
        # Si no es admin, verificar si el usuario está asociado a al menos un alojamiento
        result = await db.execute(
            select(user_accommodation).where(user_accommodation.c.user_username == username).limit(1)
        )
        has_accommodation = result.first()
        if not has_accommodation:
            raise HTTPException(
                status_code=403,
                detail="Only admin or users associated with an accommodation can create extra services"
            )

    # Crear el servicio extra
    db_extra_service = ExtraService(
        name=extra_service_data.name,
        description=extra_service_data.description,
        price=extra_service_data.price
    )
    db.add(db_extra_service)
    await db.commit()
    await db.refresh(db_extra_service)  # Refrescar para obtener el ID generado

    return ExtraServicePydantic.model_validate(db_extra_service)


async def update_extra_service(
        db: AsyncSession,
        extra_service_id: int,
        extra_service_data: ExtraServiceUpdate,
        username: str
) -> ExtraServicePydantic:
    # Verificar que el usuario exista
    result = await db.execute(select(User).where(User.username == username))
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
        select(ExtraService).where(ExtraService.id == extra_service_id)
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
    return ExtraServicePydantic.model_validate(db_extra_service)


async def delete_extra_service(db: AsyncSession, extra_service_id: int, username: str) -> None:
    # Verificar que el usuario exista
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Buscar el servicio extra con sus reservas
    result = await db.execute(
        select(ExtraService)
        .where(ExtraService.id == extra_service_id)
        .options(selectinload(ExtraService.reservations).selectinload(Reservation.room).selectinload(Room.accommodation))
    )
    db_extra_service = result.scalar_one_or_none()
    if not db_extra_service:
        raise HTTPException(status_code=404, detail="Extra service not found")

    # Validar permisos
    if user.role != "admin":
        # Si no es admin, verificar si el usuario está asociado a algún alojamiento del servicio
        allowed = False
        for reservation in db_extra_service.reservations:
            accommodation_id = reservation.room.accommodation.id
            result = await db.execute(
                select(user_accommodation).where(
                    (user_accommodation.c.user_username == username) &
                    (user_accommodation.c.accommodation_id == accommodation_id)
                )
            )
            if result.first():
                allowed = True
                break
        if not allowed:
            raise HTTPException(
                status_code=403,
                detail="Only admin or users associated with the accommodation of this service can delete it"
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


async def get_extra_service(db: AsyncSession, extra_service_id: int, username: str) -> ExtraServicePydantic:
    # Verificar que el usuario exista
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Buscar el servicio extra con sus reservas
    result = await db.execute(
        select(ExtraService)
        .where(ExtraService.id == extra_service_id)
        .options(selectinload(ExtraService.reservations).selectinload(Reservation.room).selectinload(Room.accommodation))
    )
    db_extra_service = result.scalar_one_or_none()
    if not db_extra_service:
        raise HTTPException(status_code=404, detail="Extra service not found")

    # Si es admin, permitir acceso
    if user.role == "admin":
        return ExtraServicePydantic.model_validate(db_extra_service)

    # Si no es admin, verificar si el usuario está asociado al alojamiento a través de user_accommodation
    for reservation in db_extra_service.reservations:
        accommodation_id = reservation.room.accommodation.id
        result = await db.execute(
            select(user_accommodation).where(
                (user_accommodation.c.user_username == username) &
                (user_accommodation.c.accommodation_id == accommodation_id)
            )
        )
        user_accommodation_record = result.first()
        if user_accommodation_record:
            return ExtraServicePydantic.model_validate(db_extra_service)

    # Si no se encuentra ninguna coincidencia, denegar acceso
    raise HTTPException(
        status_code=403,
        detail="Only admin or users associated with the accommodation of this service can view it"
    )


async def get_all_extra_services(db: AsyncSession, username: str) -> List[ExtraServicePydantic]:
    # Verificar que el usuario exista
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Si es admin, devolver todos los servicios extras
    if user.role == "admin":
        result = await db.execute(
            select(ExtraService)
            .options(selectinload(ExtraService.reservations).selectinload(Reservation.room).selectinload(Room.accommodation))
        )
        db_extra_services = result.scalars().all()
        return [ExtraServicePydantic.model_validate(service) for service in db_extra_services]

    # Si no es admin, filtrar por alojamientos asociados al usuario en user_accommodation
    result = await db.execute(
        select(ExtraService)
        .join(ExtraService.reservations)
        .join(Reservation.room)
        .join(Room.accommodation)
        .join(user_accommodation, user_accommodation.c.accommodation_id == Accommodation.id)
        .where(user_accommodation.c.user_username == username)
        .options(selectinload(ExtraService.reservations).selectinload(Reservation.room).selectinload(Room.accommodation))
    )
    db_extra_services = result.scalars().all()
    return [ExtraServicePydantic.model_validate(service) for service in db_extra_services]