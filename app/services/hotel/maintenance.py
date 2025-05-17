import logging
from typing import List
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.models.pydantic_models import Maintenance, MaintenanceCreate, MaintenanceUpdate
from app.models.sqlalchemy_models import Maintenance as MaintenanceTable, UserTable, Room as RoomTable, Accommodation as AccommodationTable, Reservation
from datetime import date, datetime

logger = logging.getLogger(__name__)

async def create_maintenance(db: AsyncSession, maintenance_data: MaintenanceCreate, username: str, role: str) -> Maintenance:
    """
    Crea una nueva solicitud de mantenimiento.

    Args:
        db: Sesión de base de datos asíncrona.
        maintenance_data: Datos del mantenimiento (descripción, prioridad, etc.).
        username: Nombre de usuario autenticado.
        role: Rol del usuario (admin, employee, client).

    Returns:
        Maintenance: Objeto Pydantic con los datos del mantenimiento creado, con fechas en formato YYYY-MM-DD.

    Raises:
        HTTPException: Si el usuario, habitación, o alojamiento no existen, o si los permisos no son válidos.
    """
    # Validar usuario
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Validar habitación y alojamiento
    result = await db.execute(
        select(RoomTable).where(RoomTable.id == maintenance_data.room_id)
    )
    room = result.scalar_one_or_none()
    if not room or room.accommodation_id != maintenance_data.accommodation_id:
        raise HTTPException(status_code=404, detail="Room or accommodation not found or mismatched")

    # Validar permisos
    if role == "client":
        # Clientes solo pueden crear mantenimientos para habitaciones con reservas activas
        result = await db.execute(
            select(Reservation)
            .where(
                Reservation.user_username == username,
                Reservation.room_id == maintenance_data.room_id,
                Reservation.status == "confirmed",
                Reservation.start_date <= datetime.utcnow().date(),
                Reservation.end_date >= datetime.utcnow().date()
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Client not authorized: no active reservation for this room")
    elif role == "employee":
        # Empleados solo para alojamientos en user_accommodation
        result = await db.execute(
            select(AccommodationTable)
            .join(AccommodationTable.users)
            .where(
                AccommodationTable.id == maintenance_data.accommodation_id,
                UserTable.username == username
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Employee not authorized for this accommodation")
    # Admins tienen acceso total

    # Validar assigned_to si se proporciona
    if maintenance_data.assigned_to:
        result = await db.execute(
            select(UserTable).where(
                UserTable.username == maintenance_data.assigned_to,
                UserTable.role.in_(["admin", "employee"])
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Assigned user not found or not an admin/employee")

    # Crear mantenimiento
    maintenance = MaintenanceTable(
        description=maintenance_data.description,
        priority=maintenance_data.priority,
        room_id=maintenance_data.room_id,
        accommodation_id=maintenance_data.accommodation_id,
        created_by=username,
        assigned_to=maintenance_data.assigned_to
    )
    db.add(maintenance)
    await db.commit()
    await db.refresh(maintenance)
    logger.info(f"Maintenance {maintenance.id} created by {username} for room {maintenance.room_id}")

    # Formatear fechas a YYYY-MM-DD
    maintenance_response = Maintenance.model_validate(maintenance)
    maintenance_response.created_at = maintenance.created_at.strftime("%Y-%m-%d")
    maintenance_response.updated_at = maintenance.updated_at.strftime("%Y-%m-%d")
    return maintenance_response

async def get_maintenances(
        db: AsyncSession,
        username: str,
        accommodation_id: int = None,
        room_id: int = None,
        status: str = None
) -> List[Maintenance]:
    """
    Lista mantenimientos con filtros opcionales.

    Args:
        db: Sesión de base de datos asíncrona.
        username: Nombre de usuario autenticado.
        accommodation_id: Filtro opcional por alojamiento.
        room_id: Filtro opcional por habitación.
        status: Filtro opcional por estado (pending, in_progress, completed).

    Returns:
        List[Maintenance]: Lista de mantenimientos que cumplen los filtros y permisos.

    Raises:
        HTTPException: Si el usuario no existe.
    """
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    query = select(MaintenanceTable).options(
        selectinload(MaintenanceTable.room),
        selectinload(MaintenanceTable.accommodation)
    )
    if accommodation_id:
        query = query.where(MaintenanceTable.accommodation_id == accommodation_id)
    if room_id:
        query = query.where(MaintenanceTable.room_id == room_id)
    if status:
        if status not in [s.value for s in MaintenanceTable.status.enum]:
            raise HTTPException(status_code=400, detail="Invalid status value")
        query = query.where(MaintenanceTable.status == status)

    if user.role == "client":
        # Clientes solo ven sus propios mantenimientos
        query = query.where(MaintenanceTable.created_by == username)
    elif user.role == "employee":
        # Empleados ven mantenimientos de alojamientos asociados
        result = await db.execute(
            select(AccommodationTable)
            .join(AccommodationTable.users)
            .where(UserTable.username == username)
        )
        allowed_accommodations = [a.id for a in result.scalars().all()]
        if not allowed_accommodations:
            return []
        query = query.where(MaintenanceTable.accommodation_id.in_(allowed_accommodations))
    # Admins ven todo

    result = await db.execute(query)
    maintenances = result.scalars().all()
    # Formatear fechas a YYYY-MM-DD
    return [
        Maintenance.model_validate(m).model_copy(
            update={
                "created_at": m.created_at.strftime("%Y-%m-%d"),
                "updated_at": m.updated_at.strftime("%Y-%m-%d")
            }
        ) for m in maintenances
    ]

async def update_maintenance(
        db: AsyncSession,
        maintenance_id: int,
        maintenance_data: MaintenanceUpdate,
        username: str,
        role: str
) -> Maintenance:
    """
    Actualiza un mantenimiento existente, actualizando updated_at pero no created_at.

    Args:
        db: Sesión de base de datos asíncrona.
        maintenance_id: ID del mantenimiento a actualizar.
        maintenance_data: Datos actualizados (parciales).
        username: Nombre de usuario autenticado.
        role: Rol del usuario.

    Returns:
        Maintenance: Objeto Pydantic con los datos actualizados, con fechas en formato YYYY-MM-DD.

    Raises:
        HTTPException: Si el mantenimiento no existe o el usuario no tiene permisos.
    """
    result = await db.execute(
        select(MaintenanceTable)
        .where(MaintenanceTable.id == maintenance_id)
        .options(selectinload(MaintenanceTable.room), selectinload(MaintenanceTable.accommodation))
    )
    maintenance = result.scalar_one_or_none()
    if not maintenance:
        raise HTTPException(status_code=404, detail="Maintenance not found")

    # Validar permisos
    if role == "client" and maintenance.created_by != username:
        raise HTTPException(status_code=403, detail="Client not authorized to update this maintenance")
    elif role == "employee":
        result = await db.execute(
            select(AccommodationTable)
            .join(AccommodationTable.users)
            .where(
                AccommodationTable.id == maintenance.accommodation_id,
                UserTable.username == username
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Employee not authorized for this accommodation")
    # Admins tienen acceso total

    # Validar assigned_to si se actualiza
    if maintenance_data.assigned_to:
        result = await db.execute(
            select(UserTable).where(
                UserTable.username == maintenance_data.assigned_to,
                UserTable.role.in_(["admin", "employee"])
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Assigned user not found or not an admin/employee")

    # Actualizar campos proporcionados
    update_data = maintenance_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(maintenance, key, value)

    # Actualizar updated_at explícitamente
    maintenance.updated_at = date.today()

    await db.commit()
    await db.refresh(maintenance)
    logger.info(f"Maintenance {maintenance.id} updated by {username}")

    # Formatear fechas a YYYY-MM-DD
    maintenance_response = Maintenance.model_validate(maintenance)
    maintenance_response.created_at = maintenance.created_at.strftime("%Y-%m-%d")
    maintenance_response.updated_at = maintenance.updated_at.strftime("%Y-%m-%d")
    return maintenance_response

async def delete_maintenance(db: AsyncSession, maintenance_id: int, username: str, role: str) -> None:
    """
    Elimina un mantenimiento existente.

    Args:
        db: Sesión de base de datos asíncrona.
        maintenance_id: ID del mantenimiento a eliminar.
        username: Nombre de usuario autenticado.
        role: Rol del usuario.

    Raises:
        HTTPException: Si el mantenimiento no existe o el usuario no tiene permisos.
    """
    result = await db.execute(
        select(MaintenanceTable).where(MaintenanceTable.id == maintenance_id)
    )
    maintenance = result.scalar_one_or_none()
    if not maintenance:
        raise HTTPException(status_code=404, detail="Maintenance not found")

    # Validar permisos
    if role == "client":
        raise HTTPException(status_code=403, detail="Clients cannot delete maintenances")
    elif role == "employee":
        result = await db.execute(
            select(AccommodationTable)
            .join(AccommodationTable.users)
            .where(
                AccommodationTable.id == maintenance.accommodation_id,
                UserTable.username == username
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Employee not authorized for this accommodation")
    # Admins tienen acceso total

    await db.delete(maintenance)
    await db.commit()
    logger.info(f"Maintenance {maintenance_id} deleted by {username}")