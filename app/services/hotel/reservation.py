from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.pydantic_models import Reservation, ReservationBase, ReservationUpdate
from app.models.sqlalchemy_models import (
    Reservation as ReservationTable,
    UserTable,
    Room as RoomTable,
    Accommodation,
    Maintenance as MaintenanceTable,
    MaintenanceStatus
)
from sqlalchemy.orm import selectinload
from app.utils.email import send_reservation_confirmation
from datetime import timedelta, datetime
from typing import Dict, Any
import logging
import asyncio

logger = logging.getLogger(__name__)

async def _send_confirmation_email(email: str, reservation_details: dict):
    """
    Coroutine auxiliar para enviar el correo de confirmación o actualización y manejar excepciones.

    Args:
        email: Dirección de correo del destinatario.
        reservation_details: Diccionario con los detalles de la reserva, incluyendo 'title' y 'message'.
    """
    try:
        success = await send_reservation_confirmation(email, reservation_details)
        if not success:
            logger.warning(f"No se pudo enviar el correo a {email}")
    except Exception as e:
        logger.error(f"Error al enviar el correo a {email}: {str(e)}")

async def create_reservation(db: AsyncSession, reservation_data: ReservationBase, current_username: str, current_role: str) -> Reservation:
    """
    Crea una nueva reserva, validando que la habitación no tenga mantenimientos activos que impidan la reserva.
    El envío del correo de confirmación se realiza en una tarea asíncrona en segundo plano.

    Args:
        db: Sesión de base de datos asíncrona.
        reservation_data: Datos de la reserva (fechas, habitación, etc.).
        current_username: Nombre de usuario autenticado.
        current_role: Rol del usuario (admin, employee, client).

    Returns:
        Reservation: Objeto Pydantic con los datos de la reserva creada, con fechas en formato YYYY-MM-DD.

    Raises:
        HTTPException: Si el usuario, habitación, o alojamiento no existen, hay conflictos de fechas,
                       la habitación tiene mantenimientos activos que impidan la reserva, o los permisos no son válidos.
    """
    # Validar usuario autenticado
    result = await db.execute(select(UserTable).where(UserTable.username == current_username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Authenticated user not found")

    # Determinar el username a usar: el especificado o el del usuario autenticado
    target_username = reservation_data.user_username if reservation_data.user_username is not None else current_username

    # Validar que el usuario especificado exista
    result = await db.execute(select(UserTable).where(UserTable.username == target_username))
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail=f"User {target_username} not found")

    # Validar permisos
    if current_role == "client":
        if target_username != current_username:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Clients can only create reservations for themselves"
            )
    elif current_role == "employee":
        # Empleados solo para alojamientos en user_accommodation
        result = await db.execute(
            select(Accommodation)
            .join(Accommodation.users)
            .where(
                Accommodation.id == reservation_data.accommodation_id,
                UserTable.username == current_username
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Employee not authorized for this accommodation")
    # Admins tienen acceso total

    # Validar que las fechas sean coherentes
    if reservation_data.start_date >= reservation_data.end_date:
        raise HTTPException(status_code=400, detail="Start date must be before end date")

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
            ReservationTable.status != "cancelled"
        )
    )
    existing_reservations = result.scalars().all()

    # Verificar si hay superposición de fechas con reservas
    for existing in existing_reservations:
        if (reservation_data.start_date < existing.end_date and
                reservation_data.end_date > existing.start_date):
            raise HTTPException(
                status_code=400,
                detail=f"Room {reservation_data.room_id} is already booked from {existing.start_date} to {existing.end_date}"
            )

    # Consultar mantenimientos activos (pending o in_progress) para la habitación
    result = await db.execute(
        select(MaintenanceTable).where(
            MaintenanceTable.room_id == reservation_data.room_id,
            MaintenanceTable.status.in_([MaintenanceStatus.PENDING, MaintenanceStatus.IN_PROGRESS])
        )
    )
    active_maintenances = result.scalars().all()

    # Verificar si hay mantenimientos activos que impidan la reserva
    for maintenance in active_maintenances:
        if reservation_data.start_date < maintenance.updated_at + timedelta(days=1):
            raise HTTPException(
                status_code=400,
                detail=f"Room {reservation_data.room_id} has an active maintenance (ID: {maintenance.id}, Status: {maintenance.status}, Updated: {maintenance.updated_at})"
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

    # Programar el envío del correo de confirmación en segundo plano
    if target_user.email:
        reservation_details = {
            "title": "Confirmación de Reserva",
            "message": "¡Gracias por elegir HostMaster! Su reserva ha sido creada con éxito.",
            "reservation_id": reservation.id,
            "accommodation_name": accommodation.name,
            "room_number": room.number,
            "start_date": reservation.start_date.strftime("%Y-%m-%d"),
            "end_date": reservation.end_date.strftime("%Y-%m-%d"),
            "guest_count": reservation.guest_count,
            "status": reservation.status
        }
        asyncio.create_task(_send_confirmation_email(target_user.email, reservation_details))

    # Formatear fechas a YYYY-MM-DD en la respuesta
    reservation_response = Reservation.model_validate(reservation)
    reservation_response.start_date = reservation.start_date.strftime("%Y-%m-%d")
    reservation_response.end_date = reservation.end_date.strftime("%Y-%m-%d")
    return reservation_response

async def get_reservations(db: AsyncSession, username: str) -> list[Reservation]:
    """
    Lista las reservas según el rol del usuario.

    Args:
        db: Sesión de base de datos asíncrona.
        username: Nombre de usuario autenticado.

    Returns:
        list[Reservation]: Lista de reservas accesibles para el usuario.

    Raises:
        HTTPException: Si el usuario no existe o el rol es inválido.
    """
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    query = select(ReservationTable).options(selectinload(ReservationTable.extra_services))

    if user.role == "client":
        # Clientes solo ven sus propias reservas
        query = query.where(ReservationTable.user_username == username)
    elif user.role == "employee":
        # Empleados solo ven reservas de alojamientos asociados
        result = await db.execute(
            select(Accommodation)
            .join(Accommodation.users)
            .where(UserTable.username == username)
        )
        allowed_accommodations = [a.id for a in result.scalars().all()]
        if not allowed_accommodations:
            return []
        query = query.where(ReservationTable.accommodation_id.in_(allowed_accommodations))
    # Admins ven todas las reservas

    result = await db.execute(query)
    reservations = result.scalars().all()
    # Formatear fechas a YYYY-MM-DD en la respuesta
    return [
        Reservation.model_validate(reservation).model_copy(
            update={
                "start_date": reservation.start_date.strftime("%Y-%m-%d"),
                "end_date": reservation.end_date.strftime("%Y-%m-%d")
            }
        ) for reservation in reservations
    ]

async def update_reservation(
        db: AsyncSession,
        reservation_id: int,
        reservation_update: ReservationUpdate,
        username: str
) -> Reservation:
    """
    Actualiza una reserva existente, validando que la habitación no tenga mantenimientos activos que impidan la reserva.
    Envía un correo de confirmación asíncrono con los detalles actualizados.

    Args:
        db: Sesión de base de datos asíncrona.
        reservation_id: ID de la reserva a actualizar.
        reservation_update: Datos actualizados (parciales).
        username: Nombre de usuario autenticado.

    Returns:
        Reservation: Objeto Pydantic con los datos actualizados, con fechas en formato YYYY-MM-DD.

    Raises:
        HTTPException: Si la reserva, usuario, o habitación no existen, hay conflictos de fechas,
                       la habitación tiene mantenimientos activos que impidan la reserva, o los permisos no son válidos.
    """
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

    # Validar permisos
    if user.role == "client":
        if db_reservation.user_username != username:
            raise HTTPException(status_code=403, detail="Clients can only update their own reservations")
    elif user.role == "employee":
        # Empleados solo para reservas en alojamientos asociados
        result = await db.execute(
            select(Accommodation)
            .join(Accommodation.users)
            .where(
                Accommodation.id == db_reservation.accommodation_id,
                UserTable.username == username
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Employee not authorized for this accommodation")
    # Admins tienen acceso total

    # Determinar el usuario destinatario del correo (nuevo o existente)
    target_username = reservation_update.user_username if reservation_update.user_username is not None else db_reservation.user_username
    result = await db.execute(
        select(UserTable).where(UserTable.username == target_username)
    )
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail=f"User {target_username} not found")

    # Validar permisos para el nuevo usuario
    if reservation_update.user_username is not None:
        # Clientes solo pueden asignar reservas a sí mismos
        if user.role == "client" and reservation_update.user_username != username:
            raise HTTPException(status_code=403, detail="Clients can only assign reservations to themselves")

    new_room_id = reservation_update.room_id if reservation_update.room_id is not None else db_reservation.room_id
    new_accommodation_id = reservation_update.accommodation_id if reservation_update.accommodation_id is not None else db_reservation.accommodation_id

    # Validar permisos para el nuevo alojamiento (si cambió)
    if new_accommodation_id != db_reservation.accommodation_id and user.role == "employee":
        result = await db.execute(
            select(Accommodation)
            .join(Accommodation.users)
            .where(
                Accommodation.id == new_accommodation_id,
                UserTable.username == username
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Employee not authorized for the new accommodation")

    # Consultar la habitación para validar y obtener el room_number
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

    # Validar el número de huéspedes
    if reservation_update.guest_count is not None:
        if reservation_update.guest_count <= 0:
            raise HTTPException(status_code=400, detail="Guest count must be greater than 0")
        if reservation_update.guest_count > room.room_type.max_guests:
            raise HTTPException(
                status_code=400,
                detail=f"Guest count ({reservation_update.guest_count}) exceeds maximum allowed ({room.room_type.max_guests}) for this room type"
            )

    # Validar fechas
    new_start_date = reservation_update.start_date if reservation_update.start_date is not None else db_reservation.start_date
    new_end_date = reservation_update.end_date if reservation_update.end_date is not None else db_reservation.end_date
    if reservation_update.start_date is not None or reservation_update.end_date is not None:
        if new_start_date >= new_end_date:
            raise HTTPException(status_code=400, detail="Start date must be before end date")

    # Validar conflictos con otras reservas
    if (reservation_update.room_id is not None or
            reservation_update.start_date is not None or
            reservation_update.end_date is not None):
        result = await db.execute(
            select(ReservationTable)
            .where(ReservationTable.room_id == new_room_id)
            .where(ReservationTable.id != reservation_id)
            .where(ReservationTable.status != "cancelled")
        )
        existing_reservations = result.scalars().all()
        for existing in existing_reservations:
            if (new_start_date < existing.end_date and new_end_date > existing.start_date):
                raise HTTPException(
                    status_code=400,
                    detail=f"Room {new_room_id} is already booked from {existing.start_date} to {existing.end_date}"
                )

    # Validar mantenimientos activos para la nueva habitación
    result = await db.execute(
        select(MaintenanceTable).where(
            MaintenanceTable.room_id == new_room_id,
            MaintenanceTable.status.in_([MaintenanceStatus.PENDING, MaintenanceStatus.IN_PROGRESS])
        )
    )
    active_maintenances = result.scalars().all()

    for maintenance in active_maintenances:
        if new_start_date < maintenance.updated_at + timedelta(days=1):
            raise HTTPException(
                status_code=400,
                detail=f"Room {new_room_id} has an active maintenance (ID: {maintenance.id}, Status: {maintenance.status}, Updated: {maintenance.updated_at})"
            )

    # Consultar el alojamiento para el correo
    result = await db.execute(
        select(Accommodation).where(Accommodation.id == new_accommodation_id)
    )
    accommodation = result.scalar_one_or_none()
    if not accommodation:
        raise HTTPException(status_code=404, detail="Accommodation not found")

    # Actualizar la reserva
    update_data = reservation_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_reservation, key, value)

    await db.commit()
    await db.refresh(db_reservation)

    # Programar el envío del correo de actualización en segundo plano
    if target_user.email:
        reservation_details = {
            "title": "Actualización de Reserva",
            "message": "Su reserva ha sido actualizada con éxito. A continuación, los detalles actualizados:",
            "reservation_id": db_reservation.id,
            "accommodation_name": accommodation.name,
            "room_number": room.number,
            "start_date": db_reservation.start_date.strftime("%Y-%m-%d"),
            "end_date": db_reservation.end_date.strftime("%Y-%m-%d"),
            "guest_count": db_reservation.guest_count,
            "status": db_reservation.status
        }
        asyncio.create_task(_send_confirmation_email(target_user.email, reservation_details))

    # Formatear fechas a YYYY-MM-DD en la respuesta
    reservation_response = Reservation.model_validate(db_reservation)
    reservation_response.start_date = db_reservation.start_date.strftime("%Y-%m-%d")
    reservation_response.end_date = db_reservation.end_date.strftime("%Y-%m-%d")
    return reservation_response

async def delete_reservation(db: AsyncSession, reservation_id: int, username: str) -> None:
    """
    Elimina una reserva existente, validando permisos de usuario.

    Args:
        db: Sesión de base de datos asíncrona.
        reservation_id: ID de la reserva a eliminar.
        username: Nombre de usuario autenticado.

    Raises:
        HTTPException: Si la reserva no existe o el usuario no tiene permisos.
    """
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

    # Validar permisos
    if user.role == "client":
        if db_reservation.user_username != username:
            raise HTTPException(status_code=403, detail="Clients can only delete their own reservations")
    elif user.role == "employee":
        # Empleados solo para reservas en alojamientos asociados
        result = await db.execute(
            select(Accommodation)
            .join(Accommodation.users)
            .where(
                Accommodation.id == db_reservation.accommodation_id,
                UserTable.username == username
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Employee not authorized for this accommodation")
    # Admins tienen acceso total

    await db.delete(db_reservation)
    await db.commit()

async def calculate_reservation_invoice(
        db: AsyncSession,
        reservation_id: int,
        username: str
) -> Dict[str, Any]:
    """
    Calcula el costo total de una reserva y devuelve los datos necesarios para generar una factura.

    Args:
        db: Sesión de base de datos asíncrona.
        reservation_id: ID de la reserva.
        username: Nombre de usuario autenticado.

    Returns:
        Dict[str, Any]: Diccionario con los datos de la factura, incluyendo:
            - Información del usuario (username, email, nombre completo, número de documento).
            - Detalles del alojamiento y habitación.
            - Fechas de la reserva (formato YYYY-MM-DD).
            - Número de huéspedes y estado de la reserva.
            - Desglose de costos: costo de la habitación, costo de servicios extras, costo total.

    Raises:
        HTTPException: Si la reserva, usuario, o alojamiento no existen, o si el usuario no tiene permisos.
    """
    # Validar usuario autenticado
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Consultar la reserva con relaciones necesarias
    result = await db.execute(
        select(ReservationTable)
        .where(ReservationTable.id == reservation_id)
        .options(
            selectinload(ReservationTable.user),
            selectinload(ReservationTable.room).selectinload(RoomTable.room_type),
            selectinload(ReservationTable.accommodation),
            selectinload(ReservationTable.extra_services)
        )
    )
    reservation = result.scalar_one_or_none()
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")

    # Validar permisos
    if user.role == "client":
        if reservation.user_username != username:
            raise HTTPException(status_code=403, detail="Clients can only view their own reservations")
    elif user.role == "employee":
        # Empleados solo para reservas en alojamientos asociados
        result = await db.execute(
            select(Accommodation)
            .join(Accommodation.users)
            .where(
                Accommodation.id == reservation.accommodation_id,
                UserTable.username == username
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Employee not authorized for this accommodation")
    # Admins tienen acceso total

    # Calcular el número de noches
    delta = reservation.end_date - reservation.start_date
    number_of_nights = delta.days
    if number_of_nights <= 0:
        raise HTTPException(status_code=400, detail="Invalid reservation dates: end_date must be after start_date")

    # Obtener el precio por noche de la habitación
    price_per_night = reservation.room.price
    room_cost = price_per_night * number_of_nights

    # Calcular el costo de los servicios extras
    extra_services_cost = 0
    extra_services_details = []
    for service in reservation.extra_services:
        service_cost = service.price or 0
        extra_services_cost += service_cost
        extra_services_details.append({
            "service_name": service.name,
            "price": service_cost
        })

    # Calcular el costo total
    total_cost = room_cost + extra_services_cost

    # Preparar los datos de la factura
    invoice_data = {
        "reservation_id": reservation.id,
        "user": {
            "username": reservation.user_username,
            "email": reservation.user.email or "N/A",
            "first_name": reservation.user.firstname,
            "last_name": reservation.user.lastname,
            "document_number": reservation.user.document_number
        },
        "accommodation": {
            "name": reservation.accommodation.name,
            "id": reservation.accommodation_id,
            "address": reservation.accommodation.address
        },
        "room": {
            "number": reservation.room.number,
            "room_type": reservation.room.room_type.name,
            "price_per_night": price_per_night
        },
        "reservation_details": {
            "start_date": reservation.start_date.strftime("%Y-%m-%d"),
            "end_date": reservation.end_date.strftime("%Y-%m-%d"),
            "number_of_nights": number_of_nights,
            "guest_count": reservation.guest_count,
            "status": reservation.status,
            "observations": reservation.observations or "N/A"
        },
        "cost_breakdown": {
            "room_cost": room_cost,
            "extra_services_cost": extra_services_cost,
            "extra_services": extra_services_details,
            "total_cost": total_cost
        },
        "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    }

    return invoice_data