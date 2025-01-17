from celery import shared_task
from django.core.mail import EmailMessage
from django.conf import settings

@shared_task
def enviar_correo_admin(ticket_id, admin_email, mensaje_admin):
    try:
        from_email = admin_email if admin_email != settings.DEFAULT_FROM_EMAIL else "noreply@altamiragroup.com.py"
        admin_email_msg = EmailMessage(
            subject=f"Nuevo ticket creado con ID: {ticket_id}",
            body=mensaje_admin,
            from_email=from_email,
            to=[admin_email]
        )
        admin_email_msg.content_subtype = 'html'
        admin_email_msg.send()
        return "Correo enviado al administrador exitosamente"
    except Exception as e:
        return f"Error al enviar correo al administrador: {str(e)}"

@shared_task
def enviar_correo_usuario(ticket_id, usuario_email, mensaje_usuario):
    try:
        user_email_msg = EmailMessage(
            subject=f"Confirmación de Creación de Ticket con ID: {ticket_id}",
            body=mensaje_usuario,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[usuario_email]
        )
        user_email_msg.content_subtype = 'html'
        user_email_msg.send()
        return "Correo enviado al usuario exitosamente"
    except Exception as e:
        return f"Error al enviar correo al usuario: {str(e)}"
