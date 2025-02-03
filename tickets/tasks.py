from celery import shared_task
from django.core.mail import EmailMessage
from django.conf import settings
import logging, time, smtplib, socket

logger = logging.getLogger(__name__)

from celery import shared_task
import smtplib, socket, time
from django.core.mail import EmailMessage
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def enviar_correo_admin(self, ticket_id, admin_email, mensaje_admin, subject):
    try:
        from_email = admin_email if admin_email != settings.DEFAULT_FROM_EMAIL else "noreply@altamiragroup.com.py"
        admin_email_msg = EmailMessage(
            subject=f"{subject}, Nro: {ticket_id}",
            body=mensaje_admin,
            from_email=from_email,
            to=[admin_email]
        )
        admin_email_msg.content_subtype = 'html'
        admin_email_msg.send()
        return "Correo enviado al administrador exitosamente"

    except (smtplib.SMTPException, socket.error) as e:
        logger.error(f"Error al enviar correo al administrador: {e}. Reintentando...")
        time.sleep(10)  # Espera antes de reintentar
        raise self.retry(exc=e, countdown=60)  # Reintenta después de 60 segundos
    except Exception as e:
        logger.error(f"Fallo crítico en el envío de correo al administrador: {e}")
        return f"Error al enviar correo al administrador: {str(e)}"
# -------------------------------------------------------------------------

@shared_task(bind=True, max_retries=3)
def enviar_correo_usuario(self, ticket_id, user_email, mensaje_usuario, subject):
    try:
        from_email = user_email if user_email != settings.DEFAULT_FROM_EMAIL else "noreply@altamiragroup.com.py"
        user_email_msg = EmailMessage(
            subject=f"{subject}, Nro: {ticket_id}",
            body=mensaje_usuario,
            from_email=from_email,
            to=[user_email]
        )
        user_email_msg.content_subtype = 'html'
        user_email_msg.send()
        return "Correo enviado al usuario exitosamente"

    except (smtplib.SMTPException, socket.error) as e:
        logger.error(f"Error al enviar correo al usuario: {e}. Reintentando...")
        time.sleep(10)
        raise self.retry(exc=e, countdown=30)
    except Exception as e:
        logger.error(f"Fallo crítico en el envío de correo al usuario: {e}")
        return f"Error al enviar correo al usuario: {str(e)}"

# -------------------------------------------------------------------------

@shared_task(bind=True, max_retries=3)
def enviar_comentario_ticket(self, subject, message, destinatarios):
    try:
        from_email = settings.DEFAULT_FROM_EMAIL
        email_msg = EmailMessage(
            subject=subject,
            body=message,
            from_email=from_email,
            to=destinatarios
        )
        email_msg.content_subtype = 'html'
        email_msg.send()

        logger.info(f"Correo enviado a {', '.join(destinatarios)}")
        return f"Correo enviado a {', '.join(destinatarios)}"

    except (smtplib.SMTPException, socket.error) as e:
        logger.error(f"Error al enviar correo a {', '.join(destinatarios)}: {e}. Reintentando...")
        time.sleep(10)
        raise self.retry(exc=e, countdown=30)
    except Exception as e:
        logger.error(f"Fallo crítico en el envío de correo: {e}")
        return f"Error al enviar correo: {str(e)}"
