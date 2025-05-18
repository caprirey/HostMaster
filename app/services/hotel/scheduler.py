from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func
from app.models.sqlalchemy_models import Reservation as ReservationTable
from app.utils.email import send_email
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

async def send_checkin_reminders(db: AsyncSession):
    """
    Envía recordatorios por correo a huéspedes con check-in mañana.
    """
    try:
        # Obtener la fecha de mañana en UTC
        tomorrow = (datetime.utcnow().date() + timedelta(days=1))
        logger.info(f"Buscando reservas con check-in para {tomorrow}")

        # Usar func.date para comparar solo la fecha
        result = await db.execute(
            select(ReservationTable)
            .where(func.date(ReservationTable.start_date) == tomorrow)
            .where(ReservationTable.status == "confirmed")
            .options(
                selectinload(ReservationTable.user),
                selectinload(ReservationTable.accommodation),
                selectinload(ReservationTable.room)
            )
        )
        reservations = result.scalars().all()
        logger.info(f"Encontradas {len(reservations)} reservas con check-in para {tomorrow}")

        for reservation in reservations:
            if reservation.user.email:
                logger.debug(f"Procesando reserva {reservation.id}, start_date: {reservation.start_date}")
                reservation_details = {
                    "title": "Recordatorio de Check-In",
                    "message": (
                        f"¡Su check-in en {reservation.accommodation.name} es mañana! "
                        "Por favor, llegue a partir de las 14:00. "
                        f"Dirección: {reservation.accommodation.address}. "
                        "Contacto: support@hostmaster.com."
                    ),
                    "reservation_id": reservation.id,
                    "accommodation_name": reservation.accommodation.name,
                    "room_number": reservation.room.number,
                    "start_date": reservation.start_date.strftime("%Y-%m-%d"),
                    "end_date": reservation.end_date.strftime("%Y-%m-%d"),
                    "guest_count": reservation.guest_count,
                    "status": reservation.status
                }
                await send_email(
                    recipient=reservation.user.email,
                    subject="Recordatorio de Check-In - HostMaster",
                    template_name="reservation_confirmation.html",
                    template_body=reservation_details
                )
                logger.info(f"Recordatorio de check-in enviado a {reservation.user.email} para reserva {reservation.id}")
            else:
                logger.warning(f"Reserva {reservation.id} no tiene email asociado")
    except Exception as e:
        logger.error(f"Error enviando recordatorios de check-in: {str(e)}", exc_info=True)

async def send_checkout_reminders(db: AsyncSession):
    """
    Envía recordatorios por correo a huéspedes con check-out mañana.
    """
    try:
        # Obtener la fecha de mañana en UTC
        tomorrow = (datetime.utcnow().date() + timedelta(days=1))
        logger.info(f"Buscando reservas con check-out para {tomorrow}")

        # Usar func.date para comparar solo la fecha
        result = await db.execute(
            select(ReservationTable)
            .where(func.date(ReservationTable.end_date) == tomorrow)
            .where(ReservationTable.status == "confirmed")
            .options(
                selectinload(ReservationTable.user),
                selectinload(ReservationTable.accommodation),
                selectinload(ReservationTable.room)
            )
        )
        reservations = result.scalars().all()
        logger.info(f"Encontradas {len(reservations)} reservas con check-out para {tomorrow}")

        for reservation in reservations:
            if reservation.user.email:
                logger.debug(f"Procesando reserva {reservation.id}, end_date: {reservation.end_date}")
                reservation_details = {
                    "title": "Recordatorio de Check-Out",
                    "message": (
                        f"¡Su check-out de {reservation.accommodation.name} es mañana! "
                        "Por favor, desocupe la habitación antes de las 11:00. "
                        "Esperamos que haya disfrutado su estancia. "
                        "Contacto: support@hostmaster.com."
                    ),
                    "reservation_id": reservation.id,
                    "accommodation_name": reservation.accommodation.name,
                    "room_number": reservation.room.number,
                    "start_date": reservation.start_date.strftime("%Y-%m-%d"),
                    "end_date": reservation.end_date.strftime("%Y-%m-%d"),
                    "guest_count": reservation.guest_count,
                    "status": reservation.status
                }
                await send_email(
                    recipient=reservation.user.email,
                    subject="Recordatorio de Check-Out - HostMaster",
                    template_name="reservation_confirmation.html",
                    template_body=reservation_details
                )
                logger.info(f"Recordatorio de check-out enviado a {reservation.user.email} para reserva {reservation.id}")
            else:
                logger.warning(f"Reserva {reservation.id} no tiene email asociado")
    except Exception as e:
        logger.error(f"Error enviando recordatorios de check-out: {str(e)}", exc_info=True)

# Inicializar el scheduler
scheduler = AsyncIOScheduler()

def setup_scheduler(db: AsyncSession):
    """
    Configura el scheduler para ejecutar recordatorios diariamente a las 8 AM -05.
    """
    # 8 AM
    scheduler.add_job(
        send_checkin_reminders,
        "cron",
        hour=8,
        minute=0,
        args=[db],
        id="checkin_reminders",
        replace_existing=True
    )
    scheduler.add_job(
        send_checkout_reminders,
        "cron",
        hour=13,
        minute=0,
        args=[db],
        id="checkout_reminders",
        replace_existing=True
    )
    scheduler.start()
    logger.info("Scheduler inicializado para recordatorios de check-in y check-out")