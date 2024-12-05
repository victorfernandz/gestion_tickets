from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Usuario, Ticket, Casos, Categoria, Comentario
from django.utils.timezone import now
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings

def root_redirect(request):
    return redirect('login')  # Redirige al nombre de la URL del login

# Vista de Login
def login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        try:
            # Valida si el usuario existe
            user = Usuario.objects.get(usuario=username)

            # Verifica la contraseña
            if password == user.contrasena:
                # Guarda el usuario en la sesión
                request.session['user_id'] = user.id
                return redirect('home')  # Redirige al Home
            else:
                messages.error(request, 'Usuario o contraseña incorrectos')
        except Usuario.DoesNotExist:
            messages.error(request, 'Usuario o contraseña incorrectos')

    return render(request, 'tickets/login.html')


# Vista de Home
def home(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')  # Redirigir al login si no hay sesión

    # Recuperar los datos del usuario autenticado
    user = Usuario.objects.get(id=user_id)
    return render(request, 'tickets/home.html', {'user': user})


# Vista de Logout
def logout(request):
    request.session.flush()  # Eliminar todos los datos de la sesión
    return redirect('login')


# Vista para crear tickets
def crear_ticket(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login') 

    usuario = Usuario.objects.get(id=user_id)

    if request.method == 'POST':
        # Obtener los datos del formulario
        tipo_caso_id = request.POST.get('tipoCaso')
        descripcion = request.POST.get('descripcion')
        prioridad = request.POST.get('prioridad')
        categoria_id = request.POST.get('categoria')

        if not tipo_caso_id or not descripcion or not categoria_id:
            messages.error(request, 'Todos los campos son obligatorios.')
        else:
            tipo_caso = Casos.objects.get(id=tipo_caso_id)
            categoria = Categoria.objects.get(id=categoria_id)
            ticket = Ticket.objects.create(
                categoria=categoria,
                usuario=usuario,
                tipoCaso=tipo_caso,
                descripcion=descripcion,
                estado=1,
                prioridad=prioridad
            )

            # Plantilla para el administrador
            admin_message = render_to_string('tickets/email_template.html', {
                'ticket_id': ticket.id,
                'usuario': usuario,
                'tipoCaso': tipo_caso.descripcion,
                'descripcion': descripcion,
                'prioridad': ticket.get_prioridad_display(),
            })

            # Enviar correo al administrador
            try:
                admin_email = EmailMessage(
                    subject=f"Nuevo ticket creado con ID: {ticket.id}",
                    body=admin_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=['soporte@altamiragroup.com.py']
                )
                admin_email.content_subtype = 'html'  # Asegurar formato HTML
                admin_email.send()
            except Exception as e:
            #    print(f"Error al enviar correo al administrador: {e}")
                messages.error(request, "No se pudo enviar el correo al administrador.")

            # Plantilla para el usuario
            user_message = render_to_string('tickets/email_template_user.html', {
                'ticket_id': ticket.id,
                'tipoCaso': tipo_caso.descripcion,
                'descripcion': descripcion,
                'prioridad': ticket.get_prioridad_display(),
            })

            # Enviar correo al usuario
            try:
                user_email = EmailMessage(
                    subject="Confirmación de Creación de Ticket",
                    body=user_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[usuario.email]
                )
                user_email.content_subtype = 'html'  # Asegurar formato HTML
                user_email.send()
            except Exception as e:
            #    print(f"Error al enviar correo al usuario: {e}")
                messages.error(request, "No se pudo enviar el correo al usuario.")

            #messages.success(request, '¡El ticket fue creado exitosamente y se enviaron los correos!')
            return redirect('listar_tickets')

    tipos_casos = Casos.objects.all()
    tipo_categoria = Categoria.objects.all()
    return render(request, 'tickets/crear_ticket.html', {'tipos_casos': tipos_casos, 'tipo_categoria': tipo_categoria})


# Vista para listar tickets
def listar_tickets(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login') 

    usuario = Usuario.objects.get(id=user_id)
    # Verificamos el rol para filtrar los tickets
    if usuario.rol.descripcion != 'ADMIN':
        tickets = Ticket.objects.filter(usuario_id=user_id)
    else:
        tickets = Ticket.objects.all()
    return render(request, 'tickets/listar_tickets.html', {'tickets': tickets})


def administrar_tickets(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')

    # Valida si el usuario es administrador
    usuario = Usuario.objects.get(id=user_id)
    if usuario.rol.descripcion != 'ADMIN':
        return redirect('home')

    tickets = Ticket.objects.all().order_by('id')
    administradores = Usuario.objects.filter(rol__descripcion='ADMIN')  # Obtener todos los administradores

    # Filtros
    filtro_estado = request.GET.get('estado')
    filtro_prioridad = request.GET.get('prioridad')
    filtro_fecha = request.GET.get('fecha')

    if filtro_estado:
        tickets = tickets.filter(estado=filtro_estado)
    if filtro_prioridad:
        tickets = tickets.filter(prioridad=filtro_prioridad)
    if filtro_fecha:
        tickets = tickets.filter(fecha_creacion__date=filtro_fecha)

    # Actualización de un ticket y asignación de administrador
    if request.method == 'POST':
        ticket_id = request.POST.get('ticket_id')
        nuevo_estado = request.POST.get('nuevo_estado')
        nueva_prioridad = request.POST.get('nueva_prioridad')
        nuevo_admin_id = request.POST.get('nuevo_admin')  # ID del administrador seleccionado
        comentario_texto = request.POST.get('comentario')

        ticket = get_object_or_404(Ticket, id=ticket_id)

        # Actualiza estado, prioridad y administrador si se proporcionan
        if nuevo_estado:
            ticket.estado = nuevo_estado
        if nueva_prioridad:
            ticket.prioridad = nueva_prioridad
        if nuevo_admin_id:
            nuevo_admin = Usuario.objects.get(id=nuevo_admin_id)
            ticket.admin_asignado = nuevo_admin

        ticket.save()

        # Enviar correo de notificación al usuario y al nuevo administrador asignado
        destinatarios = [ticket.usuario.email]
        if ticket.admin_asignado:
            destinatarios.append(ticket.admin_asignado.email)

        email_message = render_to_string('tickets/email_comentario.html', {
            'ticket': ticket,
            'comentario': comentario_texto,
            'admin': usuario,
        })
        try:
            email = EmailMessage(
                subject=f"Actualización en el Ticket {ticket.id}",
                body=email_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=destinatarios
            )
            email.content_subtype = 'html'
            email.send()
        except Exception as e:
            print(f"Error al enviar correo: {e}")

        return redirect('administrar_tickets')

    return render(request, 'tickets/administrar_tickets.html', {
        'tickets': tickets,
        'administradores': administradores  # Pasar administradores al contexto
    })



# Vista de Seguimiento del Ticket
def seguimiento_ticket(request, ticket_id):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')

    ticket = get_object_or_404(Ticket, id=ticket_id)

    # Verificar que el usuario sea el creador del ticket o admin asignado
    usuario = Usuario.objects.get(id=user_id)
    if usuario != ticket.usuario and usuario != ticket.admin_asignado:
        messages.error(request, 'No tienes permiso para ver este ticket.')
        return redirect('home')

    if request.method == 'POST':
        comentario_texto = request.POST.get('comentario')
        if comentario_texto:
            # Crear el comentario
            Comentario.objects.create(ticket=ticket, usuario=usuario, texto=comentario_texto)

            # Determinar el destinatario del correo
            destinatario = (
                ticket.admin_asignado.email if usuario == ticket.usuario else ticket.usuario.email
            )

            # Preparar y enviar el correo
            try:
                subject = f"Nuevo comentario en Ticket ID: {ticket.id}"
                message = render_to_string('tickets/email_comentario.html', {
                    'ticket': ticket,
                    'comentario': comentario_texto,
                    'usuario': usuario
                })
                email = EmailMessage(subject, message, settings.DEFAULT_FROM_EMAIL, [destinatario])
                email.content_subtype = 'html'
                email.send()
                messages.success(request, 'Comentario añadido y notificado.')
            except Exception as e:
                print(f"Error al enviar correo: {e}")
                messages.error(request, 'El comentario fue guardado, pero no se pudo enviar la notificación por correo.')
        else:
            messages.error(request, 'El comentario no puede estar vacío.')

    # Obtener comentarios en orden cronológico
    comentarios = ticket.comentarios.all().order_by('fecha_creacion')

    return render(request, 'tickets/seguimiento_ticket.html', {
        'ticket': ticket,
        'comentarios': comentarios
    })
