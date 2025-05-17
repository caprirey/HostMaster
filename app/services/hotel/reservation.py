from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.pydantic_models import Reservation, ReservationBase, ReservationUpdate
from app.models.sqlalchemy_models import Reservation as ReservationTable, UserTable, Room as RoomTable, Accommodation
from sqlalchemy.orm import selectinload
from app.utils.email import send_reservation_confirmation
import logging

logger = logging.getLogger(__name__)

async def create_reservation(db: AsyncSession, reservation_data: ReservationBase, current_username: str, current_role: str) -> Reservation:
    if current_role == "client":
        if reservation_data.user_username is not None and reservation_data.user_username != current_username:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Clients can only create reservations for themselves"
            )

    # Determinar el username a usar: el especificado o el del usuario autenticado
    target_username = reservation_data.user_username if reservation_data.user_username is not None else current_username

    # Validar que el usuario especificado exista
    result = await db.execute(select(UserTable).where(UserTable.username == target_username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"User {target_username} not found"
        )

    # Validar que las fechas sean coherentes
    if reservation_data.start_date >= reservation_data.end_date:
        raise HTTPException(
            status_code=400,
            detail="Start date must be before end date"
        )

    # Consultar la habitación y su tipo para obtener max_guests
    result = await db.execute(
        select(RoomTable)
        .where(RoomTable.id == reservation_data.room_id)
        .options(selectinload(RoomTable.room_type))
    )
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    # Validar que el accommodation_id coincida con el de la habitación
    if room.accommodation_id != reservation_data.accommodation_id:
        raise HTTPException(
            status_code=400,
            detail="The accommodation_id does not match the room's accommodation"
        )

    # Validar el número de huéspedes contra max_guests
    if reservation_data.guest_count > room.room_type.max_guests:
        raise HTTPException(
            status_code=400,
            detail=f"Guest count ({reservation_data.guest_count}) exceeds maximum allowed ({room.room_type.max_guests}) for this room type"
        )

    # Consultar reservaciones existentes para la misma habitación, excluyendo las canceladas
    result = await db.execute(
        select(ReservationTable).where(
            ReservationTable.room_id == reservation_data.room_id,
            ReservationTable.status != "cancelled"  # Excluir reservas canceladas
        )
    )
    existing_reservations = result.scalars().all()

    # Verificar si hay superposición de fechas
    for existing in existing_reservations:
        if (reservation_data.start_date < existing.end_date and
                reservation_data.end_date > existing.start_date):
            raise HTTPException(
                status_code=400,
                detail=f"Room {reservation_data.room_id} is already booked from {existing.start_date} to {existing.end_date}"
            )

    # Consultar el alojamiento para el correo
    result = await db.execute(
        select(Accommodation).where(Accommodation.id == reservation_data.accommodation_id)
    )
    accommodation = result.scalar_one_or_none()
    if not accommodation:
        raise HTTPException(status_code=404, detail="Accommodation not found")

    # Crear la nueva reservación con el username determinado
    reservation = ReservationTable(
        user_username=target_username,
        room_id=reservation_data.room_id,
        accommodation_id=reservation_data.accommodation_id,
        start_date=reservation_data.start_date,
        end_date=reservation_data.end_date,
        guest_count=reservation_data.guest_count,
        status=reservation_data.status,
        observations=reservation_data.observations
    )
    db.add(reservation)
    await db.commit()

    # Refrescar la reserva y cargar la relación extra_services
    result = await db.execute(
        select(ReservationTable)
        .where(ReservationTable.id == reservation.id)
        .options(selectinload(ReservationTable.extra_services))
    )
    reservation = result.scalar_one()

    # Enviar correo de confirmación si el usuario tiene email
    if user.email:
        reservation_details = {
            "reservation_id": reservation.id,
            "accommodation_name": accommodation.name,
            "room_number": room.number,
            "start_date": reservation.start_date.strftime("%Y-%m-%d"),
            "end_date": reservation.end_date.strftime("%Y-%m-%d"),
            "guest_count": reservation.guest_count,
            "status": reservation.status
        }
        success = await send_reservation_confirmation(user.email, reservation_details)
        if not success:
            logger.warning(f"No se pudo enviar el correo de confirmación a {user.email}")

    return Reservation.model_validate(reservation)

async def get_reservations(db: AsyncSession, username: str) -> list[Reservation]:
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.role == "admin" or user.role == "employee":
        result = await db.execute(
            select(ReservationTable)
            .options(selectinload(ReservationTable.extra_services))
        )
    elif user.role == "client":
        result = await db.execute(
            select(ReservationTable)
            .where(ReservationTable.user_username == username)
            .options(selectinload(ReservationTable.extra_services))
        )
    else:
        raise HTTPException(status_code=403, detail="Invalid role")

    reservations = result.scalars().all()
    return [Reservation.model_validate(reservation) for reservation in reservations]

async def update_reservation(
        db: AsyncSession,
        reservation_id: int,
        reservation_update: ReservationUpdate,
        username: str
) -> Reservation:
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        select(ReservationTable)
        .where(ReservationTable.id == reservation_id)
        .options(
            selectinload(ReservationTable.room).selectinload(RoomTable.room_type),
            selectinload(ReservationTable.extra_services)
        )
    )
    db_reservation = result.scalar_one_or_none()
    if not db_reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")

    if (user.role != "admin" and user.role != "employee") and db_reservation.user_username != username:
        raise HTTPException(status_code=403, detail="Not authorized to update this reservation")

    if reservation_update.user_username is not None:
        result = await db.execute(
            select(UserTable).where(UserTable.username == reservation_update.user_username)
        )
        target_user = result.scalar_one_or_none()
        if not target_user:
            raise HTTPException(
                status_code=404,
                detail=f"User {reservation_update.user_username} not found"
            )

    new_room_id = reservation_update.room_id if reservation_update.room_id is not None else db_reservation.room_id
    new_accommodation_id = reservation_update.accommodation_id if reservation_update.accommodation_id is not None else db_reservation.accommodation_id

    result = await db.execute(
        select(RoomTable)
        .where(RoomTable.id == new_room_id)
        .options(selectinload(RoomTable.room_type))
    )
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if not room.isAvailable:
        raise HTTPException(status_code=400, detail="Room is not available")

    if room.accommodation_id != new_accommodation_id:
        raise HTTPException(
            status_code=400,
            detail="The accommodation_id does not match the room's accommodation"
        )

    if reservation_update.guest_count is not None:
        if reservation_update.guest_count <= 0:
            raise HTTPException(status_code=400, detail="Guest count must be greater than 0")
        if reservation_update.guest_count > room.room_type.max_guests:
            raise HTTPException(
                status_code=400,
                detail=f"Guest count ({reservation_update.guest_count}) exceeds maximum allowed ({room.room_type.max_guests}) for this room type"
            )

    new_start_date = reservation_update.start_date if reservation_update.start_date is not None else db_reservation.start_date
    new_end_date = reservation_update.end_date if reservation_update.end_date is not None else db_reservation.end_date
    if reservation_update.start_date is not None or reservation_update.end_date is not None:
        if new_start_date >= new_end_date:
            raise HTTPException(status_code=400, detail="Start date must be before end date")

    if (reservation_update.room_id is not None or
            reservation_update.start_date is not None or
            reservation_update.end_date is not None):
        result = await db.execute(
            select(ReservationTable)
            .where(ReservationTable.room_id == new_room_id)
            .where(ReservationTable.id != reservation_id)
        )
        existing_reservations = result.scalars().all()
        for existing in existing_reservations:
            if (new_start_date < existing.end_date and new_end_date > existing.start_date):
                raise HTTPException(
                    status_code=400,
                    detail=f"Room {new_room_id} is already booked from {existing.start_date} to {existing.end_date}"
                )

    update_data = reservation_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_reservation, key, value)

    await db.commit()
    await db.refresh(db_reservation)
    return Reservation.model_validate(db_reservation)

async def delete_reservation(db: AsyncSession, reservation_id: int, username: str) -> None:
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        select(ReservationTable)
        .where(ReservationTable.id == reservation_id)
        .options(selectinload(ReservationTable.extra_services))
    )
    db_reservation = result.scalar_one_or_none()
    if not db_reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")

    if (user.role != "admin" and user.role != "employee") and db_reservation.user_username != username:
        raise HTTPException(status_code=403, detail="Not authorized to delete this reservation")

    await db.delete(db_reservation)
    await db.commit()