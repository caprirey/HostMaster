from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.pydantic_models import Reservation, ReservationBase, ReservationUpdate
from app.models.sqlalchemy_models import Reservation as ReservationTable, UserTable, Room as RoomTable
from sqlalchemy.orm import selectinload

async def create_reservation(db: AsyncSession, reservation_data: ReservationBase, username: str) -> Reservation:
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

    # Validar el número de huéspedes contra max_guests
    if reservation_data.guest_count > room.room_type.max_guests:
        raise HTTPException(
            status_code=400,
            detail=f"Guest count ({reservation_data.guest_count}) exceeds maximum allowed ({room.room_type.max_guests}) for this room type"
        )

    # Consultar reservaciones existentes para la misma habitación
    result = await db.execute(
        select(ReservationTable).where(
            ReservationTable.room_id == reservation_data.room_id
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

    # Si no hay superposición y el número de huéspedes es válido, crear la nueva reservación
    reservation = ReservationTable(
        user_username=username,
        room_id=reservation_data.room_id,
        start_date=reservation_data.start_date,
        end_date=reservation_data.end_date,
        guest_count=reservation_data.guest_count
    )
    db.add(reservation)
    await db.commit()
    await db.refresh(reservation)
    return Reservation.model_validate(reservation)

async def get_reservations(db: AsyncSession, username: str) -> list[Reservation]:
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.role == "admin":
        result = await db.execute(select(ReservationTable))
    elif user.role == "user":
        result = await db.execute(
            select(ReservationTable).where(ReservationTable.user_username == username)
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
    # Verificar que el usuario exista
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Buscar la reserva existente con su habitación
    result = await db.execute(
        select(ReservationTable)
        .where(ReservationTable.id == reservation_id)
        .options(selectinload(ReservationTable.room).selectinload(RoomTable.room_type))
    )
    db_reservation = result.scalar_one_or_none()
    if not db_reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")

    # Verificar permisos: solo el creador o un admin puede actualizar
    if user.role != "admin" and db_reservation.user_username != username:
        raise HTTPException(status_code=403, detail="Not authorized to update this reservation")

    # Determinar el room_id a validar (nuevo si se proporciona, actual si no)
    new_room_id = reservation_update.room_id if reservation_update.room_id is not None else db_reservation.room_id

    # Consultar la habitación y su tipo para obtener max_guests
    result = await db.execute(
        select(RoomTable)
        .where(RoomTable.id == new_room_id)
        .options(selectinload(RoomTable.room_type))
    )
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if not room.is_available:
        raise HTTPException(status_code=400, detail="Room is not available")

    # Validar guest_count si se proporciona
    if reservation_update.guest_count is not None:
        if reservation_update.guest_count <= 0:
            raise HTTPException(status_code=400, detail="Guest count must be greater than 0")
        if reservation_update.guest_count > room.room_type.max_guests:
            raise HTTPException(
                status_code=400,
                detail=f"Guest count ({reservation_update.guest_count}) exceeds maximum allowed ({room.room_type.max_guests}) for this room type"
            )

    # Validar fechas si se proporcionan
    new_start_date = reservation_update.start_date if reservation_update.start_date is not None else db_reservation.start_date
    new_end_date = reservation_update.end_date if reservation_update.end_date is not None else db_reservation.end_date
    if reservation_update.start_date is not None or reservation_update.end_date is not None:
        if new_start_date >= new_end_date:
            raise HTTPException(status_code=400, detail="Start date must be before end date")

    # Validar superposición de fechas si se cambia room_id, start_date o end_date
    if (reservation_update.room_id is not None or
            reservation_update.start_date is not None or
            reservation_update.end_date is not None):
        result = await db.execute(
            select(ReservationTable)
            .where(ReservationTable.room_id == new_room_id)
            .where(ReservationTable.id != reservation_id)  # Excluir la reserva actual
        )
        existing_reservations = result.scalars().all()
        for existing in existing_reservations:
            if (new_start_date < existing.end_date and new_end_date > existing.start_date):
                raise HTTPException(
                    status_code=400,
                    detail=f"Room {new_room_id} is already booked from {existing.start_date} to {existing.end_date}"
                )

    # Actualizar los campos proporcionados
    update_data = reservation_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_reservation, key, value)

    await db.commit()
    await db.refresh(db_reservation)
    return Reservation.model_validate(db_reservation)