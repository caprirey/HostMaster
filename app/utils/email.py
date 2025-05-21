from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr
from app.config.settings import (
    MAIL_USERNAME, MAIL_PASSWORD, MAIL_FROM, MAIL_PORT, MAIL_SERVER,
    MAIL_FROM_NAME, MAIL_STARTTLS, MAIL_SSL_TLS
)
from pathlib import Path
from typing import Dict, Optional
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración de FastMail para Gmail
conf = ConnectionConfig(
    MAIL_USERNAME=MAIL_USERNAME,
    MAIL_PASSWORD=MAIL_PASSWORD,
    MAIL_FROM=MAIL_FROM,
    MAIL_PORT=MAIL_PORT,
    MAIL_SERVER=MAIL_SERVER,
    MAIL_FROM_NAME=MAIL_FROM_NAME,
    MAIL_STARTTLS=MAIL_STARTTLS,
    MAIL_SSL_TLS=MAIL_SSL_TLS,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
    TEMPLATE_FOLDER=Path(__file__).parent.parent / "templates"
)

async def send_email(
        recipient: EmailStr,
        subject: str,
        template_name: str,
        template_body: Dict[str, any],
        subtype: MessageType = MessageType.html
) -> bool:
    """
    Envía un correo electrónico asíncrono.

    Args:
        recipient: Correo electrónico del destinatario.
        subject: Asunto del correo.
        template_name: Nombre del archivo de plantilla (e.g., "email_template.html").
        template_body: Diccionario con datos para renderizar la plantilla.
        subtype: Tipo de correo (html o plain).

    Returns:
        bool: True si el correo se envió correctamente, False si falló.
    """
    try:
        message = MessageSchema(
            subject=subject,
            recipients=[recipient],
            template_body=template_body,
            subtype=subtype
        )
        fm = FastMail(conf)
        await fm.send_message(message, template_name=template_name)
        logger.info(f"Correo enviado a {recipient} con asunto '{subject}'")
        return True
    except Exception as e:
        logger.error(f"Error al enviar correo a {recipient}: {str(e)}")
        return False

async def send_reservation_confirmation(
        recipient: EmailStr,
        reservation_details: Dict[str, any]
) -> bool:
    """
    Envía un correo de confirmación o actualización de reserva.

    Args:
        recipient: Correo electrónico del usuario.
        reservation_details: Diccionario con detalles de la reserva, incluyendo 'title' y 'message'.

    Returns:
        bool: True si el correo se envió correctamente, False si falló.
    """
    subject = f"{reservation_details.get('title', 'Confirmación de Reserva')} - HostMaster"
    return await send_email(
        recipient=recipient,
        subject=subject,
        template_name="reservation_confirmation.html",
        template_body=reservation_details
    )

async def send_generic_notification(
        recipient: EmailStr,
        subject: str,
        message: str
) -> bool:
    """
    Envía una notificación genérica en texto plano.

    Args:
        recipient: Correo electrónico del destinatario.
        subject: Asunto del correo.
        message: Contenido del correo.

    Returns:
        bool: True si el correo se envió correctamente, False si falló.
    """
    return await send_email(
        recipient=recipient,
        subject=subject,
        template_name="generic_notification.txt",
        template_body={"message": message},
        subtype=MessageType.plain
    )

async def send_invoice_email(
        recipient: EmailStr,
        invoice_details: Dict[str, any]
) -> bool:
    """
    Envía un correo con los detalles de la factura de una reserva.

    Args:
        recipient: Correo electrónico del usuario.
        invoice_details: Diccionario con detalles de la factura, incluyendo 'title'.

    Returns:
        bool: True si el correo se envió correctamente, False si falló.
    """
    subject = f"{invoice_details.get('title', 'Factura de Reserva')} - HostMaster"
    return await send_email(
        recipient=recipient,
        subject=subject,
        template_name="invoice_email.html",
        template_body=invoice_details
    )