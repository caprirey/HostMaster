from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func
from app.models.sqlalchemy_models import Reservation as ReservationTable, Room, RoomType, Review, Maintenance, ExtraService, reservation_extra_service
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

async def calculate_occupancy(
        db: AsyncSession,
        accommodation_id: int,
        start_date: Optional[datetime.date] = None,
        end_date: Optional[datetime.date] = None
) -> Dict[str, Any]:
    """
    Calcula el porcentaje de ocupación para un alojamiento en un período.
    Cuenta solo habitaciones únicas ocupadas por día.
    """
    end = datetime.utcnow().date()
    start = end - timedelta(days=7)
    if start_date:
        start = start_date
    if end_date:
        end = end_date

    result = await db.execute(
        select(Room).where(Room.accommodation_id == accommodation_id)
    )
    total_rooms = len(result.scalars().all())

    result = await db.execute(
        select(ReservationTable)
        .where(ReservationTable.accommodation_id == accommodation_id)
        .where(ReservationTable.status == "confirmed")
        .where(ReservationTable.start_date <= end)
        .where(ReservationTable.end_date >= start)
        .options(selectinload(ReservationTable.room))
    )
    reservations = result.scalars().all()

    occupancy_data = []
    current_date = start
    while current_date <= end:
        # Obtener habitaciones únicas ocupadas en el día
        occupied_room_ids = {
            r.room_id for r in reservations
            if r.start_date <= current_date <= r.end_date
        }
        occupied_rooms = len(occupied_room_ids)
        # Asegurar que no se exceda el total de habitaciones
        occupied_rooms = min(occupied_rooms, total_rooms) if total_rooms > 0 else 0
        occupancy_rate = (occupied_rooms / total_rooms * 100) if total_rooms > 0 else 0
        occupancy_data.append({
            "date": current_date.strftime("%Y-%m-%d"),
            "occupied_rooms": occupied_rooms,
            "occupancy_rate": round(occupancy_rate, 2)
        })
        current_date += timedelta(days=1)

    return {
        "accommodation_id": accommodation_id,
        "total_rooms": total_rooms,
        "occupancy_data": occupancy_data
    }

async def estimate_revenue(
        db: AsyncSession,
        accommodation_id: int,
        start_date: Optional[datetime.date] = None,
        end_date: Optional[datetime.date] = None
) -> Dict[str, Any]:
    """
    Estima ingresos basados en precios de habitaciones y servicios extra.
    """
    end = datetime.utcnow().date()
    start = end - timedelta(days=30)
    if start_date:
        start = start_date
    if end_date:
        end = end_date

    result = await db.execute(
        select(ReservationTable, Room, func.group_concat(ExtraService.price))
        .join(Room, Room.id == ReservationTable.room_id)
        .outerjoin(
            reservation_extra_service,
            reservation_extra_service.c.reservation_id == ReservationTable.id
        )
        .outerjoin(
            ExtraService,
            ExtraService.id == reservation_extra_service.c.extra_service_id
        )
        .where(ReservationTable.accommodation_id == accommodation_id)
        .where(ReservationTable.status == "confirmed")
        .where(ReservationTable.start_date >= start)
        .where(ReservationTable.start_date <= end)
        .group_by(ReservationTable.id)
    )
    reservations = result.all()

    total_revenue = 0
    for res, room, extra_prices in reservations:
        nights = (res.end_date - res.start_date).days
        room_revenue = room.price * nights
        extra_revenue = sum(float(p) for p in (extra_prices.split(",") if extra_prices else []))
        total_revenue += room_revenue + extra_revenue

    return {
        "accommodation_id": accommodation_id,
        "estimated_revenue": round(total_revenue, 2),
        "currency": "COP",
        "period": {"start": start.strftime("%Y-%m-%d"), "end": end.strftime("%Y-%m-%d")}
    }

async def get_reviews_summary(
        db: AsyncSession,
        accommodation_id: int,
        limit: int = 5
) -> Dict[str, Any]:
    """
    Obtiene el promedio de calificaciones y reseñas recientes.
    """
    result = await db.execute(
        select(func.avg(Review.rating))
        .where(Review.accommodation_id == accommodation_id)
    )
    avg_rating = result.scalar() or 0

    result = await db.execute(
        select(Review)
        .where(Review.accommodation_id == accommodation_id)
        .order_by(Review.created_at.desc())
        .limit(limit)
        .options(selectinload(Review.user))
    )
    reviews = result.scalars().all()

    return {
        "accommodation_id": accommodation_id,
        "average_rating": round(float(avg_rating), 1),
        "recent_reviews": [
            {
                "rating": r.rating,
                "comment": r.comment,
                "user": r.user.firstname + " " + r.user.lastname,
                "created_at": r.created_at
            } for r in reviews
        ]
    }

async def calculate_performance(
        db: AsyncSession,
        accommodation_id: int,
        start_date: Optional[datetime.date] = None,
        end_date: Optional[datetime.date] = None
) -> Dict[str, Any]:
    """
    Calcula métricas de rendimiento: reservas por habitación y tasa de cancelaciones.
    """
    end = datetime.utcnow().date()
    start = end - timedelta(days=30)
    if start_date:
        start = start_date
    if end_date:
        end = end_date

    result = await db.execute(
        select(func.count())
        .select_from(ReservationTable)
        .where(ReservationTable.accommodation_id == accommodation_id)
        .where(ReservationTable.start_date >= start)
        .where(ReservationTable.start_date <= end)
    )
    total_reservations = result.scalar() or 0

    result = await db.execute(
        select(func.count())
        .select_from(ReservationTable)
        .where(ReservationTable.accommodation_id == accommodation_id)
        .where(ReservationTable.status == "cancelled")
        .where(ReservationTable.start_date >= start)
        .where(ReservationTable.start_date <= end)
    )
    cancellations = result.scalar() or 0
    cancellation_rate = (cancellations / total_reservations * 100) if total_reservations > 0 else 0

    result = await db.execute(
        select(Room.number, func.count(ReservationTable.id))
        .join(Room, Room.id == ReservationTable.room_id)
        .where(ReservationTable.accommodation_id == accommodation_id)
        .where(ReservationTable.start_date >= start)
        .where(ReservationTable.start_date <= end)
        .group_by(Room.number)
    )
    room_bookings = [{"room_number": row[0], "bookings": row[1]} for row in result.all()]

    return {
        "accommodation_id": accommodation_id,
        "total_reservations": total_reservations,
        "cancellation_rate": round(cancellation_rate, 2),
        "room_bookings": room_bookings
    }

async def recent_activity(
        db: AsyncSession,
        accommodation_id: int
) -> Dict[str, Any]:
    """
    Lista reservas recientes, check-ins y check-outs de hoy.
    """
    today = datetime.utcnow().date()

    result = await db.execute(
        select(ReservationTable)
        .where(ReservationTable.accommodation_id == accommodation_id)
        .order_by(ReservationTable.start_date.desc())
        .limit(5)
        .options(
            selectinload(ReservationTable.room),
            selectinload(ReservationTable.user)
        )
    )
    recent_reservations = result.scalars().all()

    result = await db.execute(
        select(ReservationTable)
        .where(ReservationTable.accommodation_id == accommodation_id)
        .where(ReservationTable.start_date == today)
        .where(ReservationTable.status == "confirmed")
    )
    checkins = result.scalars().all()

    result = await db.execute(
        select(ReservationTable)
        .where(ReservationTable.accommodation_id == accommodation_id)
        .where(ReservationTable.end_date == today)
        .where(ReservationTable.status == "confirmed")
    )
    checkouts = result.scalars().all()

    return {
        "recent_reservations": [
            {
                "id": r.id,
                "room_number": r.room.number,
                "guest": r.user.firstname + " " + r.user.lastname,
                "start_date": r.start_date,
                "end_date": r.end_date
            } for r in recent_reservations
        ],
        "checkins_today": len(checkins),
        "checkouts_today": len(checkouts)
    }

async def get_maintenance_summary(
        db: AsyncSession,
        accommodation_id: int
) -> Dict[str, Any]:
    """
    Muestra tareas de mantenimiento pendientes o en progreso.
    """
    result = await db.execute(
        select(Maintenance)
        .where(Maintenance.accommodation_id == accommodation_id)
        .where(Maintenance.status.in_(["pending", "in_progress"]))
        .options(
            selectinload(Maintenance.room),
            selectinload(Maintenance.assignee)
        )
    )
    maintenances = result.scalars().all()

    return {
        "accommodation_id": accommodation_id,
        "pending_maintenances": [
            {
                "id": m.id,
                "room_number": m.room.number,
                "description": m.description,
                "priority": m.priority,
                "status": m.status,
                "assigned_to": m.assignee.firstname + " " + m.assignee.lastname if m.assignee else None
            } for m in maintenances
        ]
    }

async def daily_metrics(
        db: AsyncSession,
        accommodation_id: int,
        start_date: Optional[datetime.date] = None,
        end_date: Optional[datetime.date] = None
) -> Dict[str, Any]:
    """
    Calcula métricas diarias: ingresos, habitaciones ocupadas, tasa de ocupación, reservas y mantenimiento.
    """
    end = datetime.utcnow().date()
    start = end - timedelta(days=7)
    if start_date:
        start = start_date
    if end_date:
        end = end_date

    # Obtener total de habitaciones
    result = await db.execute(
        select(Room).where(Room.accommodation_id == accommodation_id)
    )
    total_rooms = len(result.scalars().all())

    # Obtener reservas confirmadas en el período
    result = await db.execute(
        select(ReservationTable, Room, func.group_concat(ExtraService.price))
        .join(Room, Room.id == ReservationTable.room_id)
        .outerjoin(
            reservation_extra_service,
            reservation_extra_service.c.reservation_id == ReservationTable.id
        )
        .outerjoin(
            ExtraService,
            ExtraService.id == reservation_extra_service.c.extra_service_id
        )
        .where(ReservationTable.accommodation_id == accommodation_id)
        .where(ReservationTable.status == "confirmed")
        .where(ReservationTable.start_date <= end)
        .where(ReservationTable.end_date >= start)
        .group_by(ReservationTable.id)
        .options(selectinload(ReservationTable.room))
    )
    reservations = result.all()

    # Obtener tareas de mantenimiento
    result = await db.execute(
        select(Maintenance, Room.number)
        .join(Room, Room.id == Maintenance.room_id)
        .where(Maintenance.accommodation_id == accommodation_id)
        .where(Maintenance.status.in_(["pending", "in_progress"]))
        .options(selectinload(Maintenance.room))
    )
    maintenances = result.all()

    daily_metrics = []
    current_date = start
    while current_date <= end:
        # Habitaciones ocupadas y reservas
        occupied_rooms = 0
        daily_reservations = 0
        daily_revenue = 0
        for res, room, extra_prices in reservations:
            if res.start_date <= current_date <= res.end_date:
                occupied_rooms += 1
                daily_reservations += 1
                # Prorratear ingresos por noche
                nights = (res.end_date - res.start_date).days or 1
                daily_room_revenue = room.price / nights
                daily_extra_revenue = sum(float(p) for p in (extra_prices.split(",") if extra_prices else [])) / nights
                daily_revenue += daily_room_revenue + daily_extra_revenue

        # Tasa de ocupación
        occupancy_rate = (occupied_rooms / total_rooms * 100) if total_rooms > 0 else 0

        # Mantenimiento: solo tareas creadas o actualizadas en current_date
        maintenance_issues = [
            f"Room {m[1]}: {m[0].description} ({m[0].status})"
            for m in maintenances
            if m[0].room.accommodation_id == accommodation_id
               and (
                       (m[0].created_at == current_date if m[0].created_at else False)
                       or (m[0].updated_at == current_date if m[0].updated_at else False)
               )
        ]

        daily_metrics.append({
            "date": current_date.strftime("%Y-%m-%d"),
            "revenue": round(daily_revenue, 2),
            "occupied_rooms": occupied_rooms,
            "occupancy_rate": round(occupancy_rate, 2),
            "reservations": daily_reservations,
            "maintenance_issues": maintenance_issues
        })
        current_date += timedelta(days=1)

    return {
        "accommodation_id": accommodation_id,
        "total_rooms": total_rooms,
        "daily_metrics": daily_metrics
    }




async def top_revenue_days_by_weekday(
        db: AsyncSession,
        accommodation_id: int,
        start_date: Optional[datetime.date] = None,
        end_date: Optional[datetime.date] = None
) -> Dict[str, Any]:
    """
    Calcula los ingresos totales por día de la semana para un alojamiento en un período.
    Los ingresos se prorratean por noche desde precios de habitaciones y servicios extra.
    Retorna los días de la semana ordenados de mayor a menor ingreso total.
    """
    end = datetime.utcnow().date()
    start = end - timedelta(days=30)
    if start_date:
        start = start_date
    if end_date:
        end = end_date

    if start and end and start > end:
        raise ValueError("start_date debe ser menor o igual a end_date")

    query = (
        select(
            ReservationTable.start_date,
            ReservationTable.end_date,
            Room.price,
            func.group_concat(ExtraService.price).label("extra_prices")
        )
        .join(Room, Room.id == ReservationTable.room_id)
        .outerjoin(
            reservation_extra_service,
            reservation_extra_service.c.reservation_id == ReservationTable.id
        )
        .outerjoin(
            ExtraService,
            ExtraService.id == reservation_extra_service.c.extra_service_id
        )
        .where(ReservationTable.accommodation_id == accommodation_id)
        .where(ReservationTable.status == "confirmed")
        .where(ReservationTable.end_date >= start)
        .where(ReservationTable.start_date <= end)
        .group_by(ReservationTable.id)
    )

    result = await db.execute(query)
    reservations = result.all()

    if not reservations:
        return {"accommodation_id": accommodation_id, "top_revenue_days": []}

    weekday_revenues = {i: 0.0 for i in range(7)}  # 0: Lunes, ..., 6: Domingo
    weekday_names = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

    for res in reservations:
        res_start = max(res.start_date, start) if start else res.start_date
        res_end = min(res.end_date, end) if end else res.end_date
        if res_end < res_start:
            continue
        room_price = float(res.price)
        extra_prices = [float(p) for p in (res.extra_prices.split(",") if res.extra_prices else [])]
        extra_total = sum(extra_prices)
        nights = (res.end_date - res.start_date).days or 1
        daily_total = (room_price + extra_total) / nights

        current_date = res_start
        while current_date <= res_end:
            weekday = current_date.weekday()
            weekday_revenues[weekday] += daily_total
            current_date += timedelta(days=1)

    top_revenue_days = [
        {
            "weekday": weekday_names[i],
            "total_revenue": round(revenue, 2)
        }
        for i, revenue in sorted(
            weekday_revenues.items(),
            key=lambda x: x[1],
            reverse=True
        )
        if revenue > 0
    ]

    return {
        "accommodation_id": accommodation_id,
        "top_revenue_days": top_revenue_days
    }

async def accommodation_summary(
        db: AsyncSession,
        accommodation_id: int,
        start_date: Optional[datetime.date] = None,
        end_date: Optional[datetime.date] = None
) -> Dict[str, Any]:
    """
    Calcula un resumen de métricas para un alojamiento en un período.
    Incluye ocupación, habitaciones ocupadas por tipo (porcentaje), ingresos por tipo (porcentaje),
    servicios adicionales, reservas, mantenimientos e ingresos totales.
    Limita ocupación a habitaciones únicas y tasa máxima al 100%.
    """
    end = datetime.utcnow().date()
    start = end - timedelta(days=30)
    if start_date:
        start = start_date
    if end_date:
        end = end_date

    if start and end and start > end:
        raise ValueError("start_date debe ser menor o igual a end_date")

    period_days = (end - start).days + 1 if start and end else 1

    # Total de habitaciones
    result = await db.execute(
        select(Room).where(Room.accommodation_id == accommodation_id)
    )
    rooms = result.scalars().all()
    total_rooms = len(rooms)

    # Tipos de habitación dinámicamente
    result = await db.execute(select(RoomType))
    room_types = result.scalars().all()
    rooms_by_type = {rt.name: 0 for rt in room_types}
    room_revenues = {rt.name: 0.0 for rt in room_types}

    # Contar habitaciones por tipo
    result = await db.execute(
        select(Room, RoomType.name)
        .join(RoomType, RoomType.id == Room.type_id)
        .where(Room.accommodation_id == accommodation_id)
    )
    for _, type_name in result.all():
        if type_name in rooms_by_type:
            rooms_by_type[type_name] += 1

    # Reservas confirmadas y canceladas
    result = await db.execute(
        select(ReservationTable.status, func.count())
        .where(ReservationTable.accommodation_id == accommodation_id)
        .where(ReservationTable.start_date <= end)
        .where(ReservationTable.end_date >= start)
        .group_by(ReservationTable.status)
    )
    reservation_counts = {row[0]: row[1] for row in result.all()}
    confirmed_reservations = reservation_counts.get("confirmed", 0)
    cancelled_reservations = reservation_counts.get("cancelled", 0)

    # Ocupación e ingresos
    result = await db.execute(
        select(
            ReservationTable.start_date,
            ReservationTable.end_date,
            ReservationTable.room_id,
            Room.price,
            RoomType.name.label("room_type"),
            func.group_concat(ExtraService.price).label("extra_prices")
        )
        .join(Room, Room.id == ReservationTable.room_id)
        .join(RoomType, RoomType.id == Room.type_id)
        .outerjoin(
            reservation_extra_service,
            reservation_extra_service.c.reservation_id == ReservationTable.id
        )
        .outerjoin(
            ExtraService,
            ExtraService.id == reservation_extra_service.c.extra_service_id
        )
        .where(ReservationTable.accommodation_id == accommodation_id)
        .where(ReservationTable.status == "confirmed")
        .where(ReservationTable.end_date >= start)
        .where(ReservationTable.start_date <= end)
        .group_by(ReservationTable.id)
    )
    reservations = result.all()

    extra_service_revenue = 0.0
    extra_service_count = 0
    total_revenue = 0.0
    occupied_days_by_type = {rt.name: 0 for rt in room_types}
    total_occupied_days = 0

    # Calcular ocupación por día con habitaciones únicas
    current_date = start
    while current_date <= end:
        occupied_room_ids = {
            r.room_id for r in reservations
            if r.start_date <= current_date <= r.end_date
        }
        occupied_rooms = min(len(occupied_room_ids), total_rooms) if total_rooms > 0 else 0
        total_occupied_days += occupied_rooms

        # Contar por tipo de habitación
        occupied_types = await db.execute(
            select(RoomType.name)
            .join(Room, Room.type_id == RoomType.id)
            .where(Room.id.in_(occupied_room_ids))
        )
        for (type_name,) in occupied_types.all():
            if type_name in occupied_days_by_type:
                occupied_days_by_type[type_name] += 1

        current_date += timedelta(days=1)

    # Calcular ingresos
    for res in reservations:
        res_start = max(res.start_date, start) if start else res.start_date
        res_end = min(res.end_date, end) if end else res.end_date
        if res_end < res_start:
            continue
        room_price = float(res.price)
        extra_prices = [float(p) for p in (res.extra_prices.split(",") if res.extra_prices else [])]
        extra_total = sum(extra_prices)
        nights = (res.end_date - res.start_date).days or 1
        daily_total = (room_price + extra_total) / nights

        current_date = res_start
        while current_date <= res_end:
            if res.room_type in room_revenues:
                room_revenues[res.room_type] += daily_total - extra_total
            extra_service_revenue += extra_total / nights
            if extra_prices:
                extra_service_count += 1
            total_revenue += daily_total
            current_date += timedelta(days=1)

    # Tasa de ocupación general (limitada al 100%)
    occupancy_rate = min((total_occupied_days / (total_rooms * period_days) * 100) if total_rooms > 0 else 0, 100)

    # Promedio de habitaciones ocupadas (limitado a total_rooms)
    avg_occupied_rooms = min(total_occupied_days / period_days if period_days > 0 else 0, total_rooms)

    # Porcentaje de ocupación por tipo respecto al total de ocupación
    avg_occupied_sencilla = (occupied_days_by_type.get("Habitación Sencilla", 0) / total_occupied_days * 100) if total_occupied_days > 0 else 0
    avg_occupied_doble = (occupied_days_by_type.get("Habitación Doble", 0) / total_occupied_days * 100) if total_occupied_days > 0 else 0
    avg_occupied_familiar = (occupied_days_by_type.get("Habitación Familiar", 0) / total_occupied_days * 100) if total_occupied_days > 0 else 0

    # Porcentaje de ingresos por tipo respecto al total
    avg_revenue_sencilla = (room_revenues.get("Habitación Sencilla", 0) / total_revenue * 100) if total_revenue > 0 else 0
    avg_revenue_doble = (room_revenues.get("Habitación Doble", 0) / total_revenue * 100) if total_revenue > 0 else 0
    avg_revenue_familiar = (room_revenues.get("Habitación Familiar", 0) / total_revenue * 100) if total_revenue > 0 else 0

    # Promedio de servicios adicionales por habitación
    avg_extra_services_per_room = extra_service_count / total_occupied_days if total_occupied_days > 0 else 0

    # Mantenimientos
    result = await db.execute(
        select(func.count())
        .select_from(Maintenance)
        .where(Maintenance.accommodation_id == accommodation_id)
        .where(Maintenance.created_at >= start)
        .where(Maintenance.created_at <= end)
    )
    maintenance_count = result.scalar() or 0

    # Ingreso promedio por día
    avg_daily_revenue = total_revenue / period_days if period_days > 0 else 0

    return {
        "accommodation_id": accommodation_id,
        "period": {"start": start.strftime("%Y-%m-%d"), "end": end.strftime("%Y-%m-%d")},
        "summary": {
            "occupancy_rate": round(occupancy_rate, 2),
            "avg_occupied_rooms": round(avg_occupied_rooms, 2),
            "avg_occupied_sencilla": round(avg_occupied_sencilla, 2),
            "avg_occupied_doble": round(avg_occupied_doble, 2),
            "avg_occupied_familiar": round(avg_occupied_familiar, 2),
            "avg_revenue_sencilla": round(avg_revenue_sencilla, 2),
            "avg_revenue_doble": round(avg_revenue_doble, 2),
            "avg_revenue_familiar": round(avg_revenue_familiar, 2),
            "avg_extra_services_per_room": round(avg_extra_services_per_room, 2),
            "extra_service_revenue": round(extra_service_revenue, 2),
            "confirmed_reservations": confirmed_reservations,
            "cancelled_reservations": cancelled_reservations,
            "maintenance_incidents": maintenance_count,
            "avg_daily_revenue": round(avg_daily_revenue, 2),
            "total_revenue": round(total_revenue, 2)
        }
    }