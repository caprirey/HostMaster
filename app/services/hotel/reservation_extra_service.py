# app/services/hotel/reservation_extra_service.py
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import insert, update, delete
from app.models.sqlalchemy_models import UserTable, Reservation, ExtraService, reservation_extra_service
from app.models.pydantic_models import ReservationExtraService, ReservationExtraServiceCreate, \
    ReservationExtraServiceUpdate
from typing import List

async def create_reservation_extra_service(
        db: AsyncSession, reservation_extra_data: ReservationExtraServiceCreate, username: str
) -> ReservationExtraService:
    # Verificar que el usuario exista
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verificar que la reserva exista
    result = await db.execute(
        select(Reservation).where(Reservation.id == reservation_extra_data.reservation_id)
    )
    reservation = result.scalar_one_or_none()
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")

    # Validar permisos: solo el propietario de la reserva o admin pueden añadir servicios extras
    if user.role != "admin" and reservation.user_username != username:
        raise HTTPException(
            status_code=403,
            detail="Only admin or the reservation owner can add extra services"
        )

    # Verificar que el servicio extra exista
    result = await db.execute(
        select(ExtraService).where(ExtraService.id == reservation_extra_data.extra_service_id)
    )
    extra_service = result.scalar_one_or_none()
    if not extra_service:
        raise HTTPException(status_code=404, detail="Extra service not found")

    # Verificar si la relación ya existe
    result = await db.execute(
        select(reservation_extra_service).where(
            reservation_extra_service.c.reservation_id == reservation_extra_data.reservation_id,
            reservation_extra_service.c.extra_service_id == reservation_extra_data.extra_service_id
        )
    )
    existing_relation = result.first()
    if existing_relation:
        raise HTTPException(status_code=400, detail="This extra service is already associated with the reservation")

    # Crear la relación en la tabla intermedia
    stmt = insert(reservation_extra_service).values(
        reservation_id=reservation_extra_data.reservation_id,
        extra_service_id=reservation_extra_data.extra_service_id
    )
    await db.execute(stmt)
    await db.commit()

    return ReservationExtraService(
        reservation_id=reservation_extra_data.reservation_id,
        extra_service_id=reservation_extra_data.extra_service_id
    )


async def update_reservation_extra_service(
        db: AsyncSession,
        reservation_id: int,
        reservation_extra_data: ReservationExtraServiceUpdate,
        username: str
) -> ReservationExtraService:
    # Verificar que el usuario exista
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verificar que la reserva exista
    result = await db.execute(
        select(Reservation).where(Reservation.id == reservation_id)
    )
    reservation = result.scalar_one_or_none()
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")

    # Validar permisos: solo el propietario de la reserva o admin pueden modificar servicios extras
    if user.role != "admin" and reservation.user_username != username:
        raise HTTPException(
            status_code=403,
            detail="Only admin or the reservation owner can update extra services"
        )

    # Verificar que el nuevo servicio extra exista
    result = await db.execute(
        select(ExtraService).where(ExtraService.id == reservation_extra_data.extra_service_id)
    )
    extra_service = result.scalar_one_or_none()
    if not extra_service:
        raise HTTPException(status_code=404, detail="Extra service not found")

    # Verificar que la relación original existe
    result = await db.execute(
        select(reservation_extra_service).where(
            reservation_extra_service.c.reservation_id == reservation_id
        )
    )
    existing_relation = result.first()
    if not existing_relation:
        raise HTTPException(status_code=404, detail="No extra service association found for this reservation")

    # Actualizar la relación en la tabla intermedia
    stmt = (
        update(reservation_extra_service)
        .where(reservation_extra_service.c.reservation_id == reservation_id)
        .values(extra_service_id=reservation_extra_data.extra_service_id)
    )
    result = await db.execute(stmt)
    if result.rowcount == 0:
        raise HTTPException(status_code=400, detail="Failed to update the extra service association")

    await db.commit()

    return ReservationExtraService(
        reservation_id=reservation_id,
        extra_service_id=reservation_extra_data.extra_service_id
    )

async def delete_reservation_extra_service(
        db: AsyncSession,
        reservation_id: int,
        extra_service_id: int,
        username: str
) -> None:
    # Verificar que el usuario exista
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verificar que la reserva exista
    result = await db.execute(
        select(Reservation).where(Reservation.id == reservation_id)
    )
    reservation = result.scalar_one_or_none()
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")

    # Validar permisos: solo el propietario de la reserva o admin pueden eliminar servicios extras
    if user.role != "admin" and reservation.user_username != username:
        raise HTTPException(
            status_code=403,
            detail="Only admin or the reservation owner can delete extra services"
        )

    # Verificar que la relación existe
    result = await db.execute(
        select(reservation_extra_service).where(
            reservation_extra_service.c.reservation_id == reservation_id,
            reservation_extra_service.c.extra_service_id == extra_service_id
        )
    )
    existing_relation = result.first()
    if not existing_relation:
        raise HTTPException(status_code=404, detail="Extra service association not found for this reservation")

    # Eliminar la relación
    stmt = delete(reservation_extra_service).where(
        reservation_extra_service.c.reservation_id == reservation_id,
        reservation_extra_service.c.extra_service_id == extra_service_id
    )
    result = await db.execute(stmt)
    if result.rowcount == 0:
        raise HTTPException(status_code=400, detail="Failed to delete the extra service association")

    await db.commit()



async def get_reservation_extra_services(
            db: AsyncSession,
            reservation_id: int,
            username: str
    ) -> List[ReservationExtraService]:
    # Verificar que el usuario exista
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verificar que la reserva exista
    result = await db.execute(
        select(Reservation).where(Reservation.id == reservation_id)
    )
    reservation = result.scalar_one_or_none()
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")

    # Validar permisos: solo el propietario de la reserva o admin pueden ver los servicios extras
    if user.role != "admin" and reservation.user_username != username:
        raise HTTPException(
            status_code=403,
            detail="Only admin or the reservation owner can view extra services"
        )

    # Obtener todas las relaciones para la reserva
    result = await db.execute(
        select(reservation_extra_service).where(
            reservation_extra_service.c.reservation_id == reservation_id
        )
    )
    relations = result.fetchall()

    if not relations:
        return []  # Devolver lista vacía si no hay servicios extras asociados

    # Mapear los resultados a objetos Pydantic
    return [
        ReservationExtraService(
            reservation_id=row.reservation_id,
            extra_service_id=row.extra_service_id
        )
        for row in relations
    ]