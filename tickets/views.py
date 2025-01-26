from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Usuario, Ticket, Casos, Categoria, Comentario
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from django.http import JsonResponse
from .tasks import enviar_correo_admin, enviar_correo_usuario, enviar_comentario_ticket 
from datetime import timedelta
from django.contrib.auth.hashers import make_password, check_password

# Vista de Login
def login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        try:
            user = Usuario.objects.get(usuario=username)

            # Verifica la contraseña usando check_password
            if check_password(password, user.contrasena):
                # Redirige al cambio de contraseña si es necesario
                if user.necesita_cambiar_contrasena:
                    request.session['user_id'] = user.id
                    return redirect('cambiar_contrasena', user_id=user.id)

                # Si no necesita cambiar contraseña, procede al home
                request.session['user_id'] = user.id
                return redirect('home')
            else:
                messages.error(request, 'Usuario o contraseña incorrectos.')
        except Usuario.DoesNotExist:
            messages.error(request, 'Usuario o contraseña incorrectos.')

    return render(request, 'tickets/login.html')

# Vista de Home
def home(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')

    user = Usuario.objects.get(id=user_id)
    return render(request, 'tickets/home.html', {'user': user})

# Vista de Logout
def logout(request):
    request.session.flush()  
    return redirect('login')

# Vista para cambiar la contraseña
def cambiar_contrasena(request, user_id):
    usuario = get_object_or_404(Usuario, id=user_id)

    if request.method == 'POST':
        contrasena_actual = request.POST.get('contrasena_actual')
        nueva_contrasena = request.POST.get('nueva_contrasena')
        confirmar_contrasena = request.POST.get('confirmar_contrasena')

        # Verifica la contraseña actual
        if not check_password(contrasena_actual, usuario.contrasena):
            messages.error(request, 'La contraseña actual es incorrecta.')
            return redirect('cambiar_contrasena', user_id=user_id)

        # Verifica que las contraseñas coincidan
        if nueva_contrasena != confirmar_contrasena:
            messages.error(request, 'Las contraseñas no coinciden.')
            return redirect('cambiar_contrasena', user_id=user_id)
        
        if nueva_contrasena == contrasena_actual:
            messages.error(request, 'La nueva contraseña no puede ser igual a la actual.')
            return redirect('cambiar_contrasena', user_id=user_id)

        # Cifra y guarda la nueva contraseña
        usuario.contrasena = make_password(nueva_contrasena)
        usuario.necesita_cambiar_contrasena = False
        usuario.save()

        messages.success(request, '¡Contraseña actualizada con éxito!')
        return redirect('home')

    return render(request, 'tickets/cambiar_contrasena.html', {'usuario': usuario})

# Creción de tickets
def crear_ticket(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login') 

    usuario = Usuario.objects.get(id=user_id)

    # Si es una petición AJAX para filtrar casos por categoría
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        categoria_id = request.GET.get('categoria_id')
        if categoria_id:
            if categoria_id == '4':
                # Si la categoría seleccionada es la 4 (Urgente)
                # Mostrar sólo los casos con categoria_id=4
                casos = Casos.objects.filter(categoria=4)
            elif categoria_id == '3':
                casos = Casos.objects.filter(categoria=3)
            elif categoria_id == '2':
                casos = Casos.objects.filter(categoria=2)
            elif categoria_id == '1':
                casos = Casos.objects.filter(categoria=1)
            else :
                # mostrar casos que tengan categoria null
                casos = Casos.objects.exclude(categoria=4)
            
            data = {
                'casos': [{'id': c.id, 'descripcion': c.descripcion} for c in casos]
            }
            return JsonResponse(data)
        else:
            # Si no se proporcionó categoria_id, retornar un listado vacío
            return JsonResponse({'casos': []})

    # Si es un POST normal (envío del formulario para crear el ticket)
    if request.method == 'POST':
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

            # Generar los mensajes para los correos
            mensaje_admin = render_to_string('tickets/email_template.html', {
                'ticket_id': ticket.id,
                'usuario': usuario,
                'tipoCaso': tipo_caso.descripcion,
                'descripcion': descripcion,
                'prioridad': ticket.get_prioridad_display(),
            })

            mensaje_usuario = render_to_string('tickets/email_template_user.html', {
                'ticket_id': ticket.id,
                'tipoCaso': tipo_caso.descripcion,
                'descripcion': descripcion,
                'prioridad': ticket.get_prioridad_display(),
            })

            # Delegar el envío de correos a Celery
            enviar_correo_admin.delay(
                ticket.id, 
                'soporte@altamiragroup.com.py', 
                mensaje_admin
            )

            enviar_correo_usuario.delay(
                ticket.id, 
                usuario.email, 
                mensaje_usuario
            )

            messages.success(request, 'Ticket creado con éxito.')
            return redirect('listar_tickets')

     # Si es un GET normal, mostrar el formulario sin AJAX
    tipo_categoria = Categoria.objects.all()
    return render(request, 'tickets/crear_ticket.html', {'tipo_categoria': tipo_categoria})
        
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
        tickets = Ticket.objects.all().order_by('id')
    return render(request, 'tickets/listar_tickets.html', {'tickets': tickets})

# Vista para la administración de tickets
def administrar_tickets(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')

    # Valida si el usuario es administrador
    usuario = Usuario.objects.get(id=user_id)
    if usuario.rol.descripcion != 'ADMIN':
        return redirect('home')

    tickets = Ticket.objects.all().order_by('id')
    administradores = Usuario.objects.filter(rol__descripcion='ADMIN')

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
        nuevo_admin_id = request.POST.get('nuevo_admin')
        comentario_texto = request.POST.get('comentario')
        nuevo_tiempo_resolucion = request.POST.get('tiempo_resolucion')

        ticket = get_object_or_404(Ticket, id=ticket_id)

        # Actualiza el tiempo de resolución
        if nuevo_tiempo_resolucion:
            horas, minutos = map(int, nuevo_tiempo_resolucion.split(':'))
            ticket.tiempo_resolucion = timedelta(hours=horas, minutes=minutos)

        # Actualiza estado, prioridad y administrador si se proporcionan
        if nuevo_estado:
            ticket.estado = nuevo_estado
        if nueva_prioridad:
            ticket.prioridad = nueva_prioridad
        if nuevo_admin_id:
            nuevo_admin = Usuario.objects.get(id=nuevo_admin_id)
            ticket.admin_asignado = nuevo_admin

        ticket.save()

        # Se envía correo de notificación al usuario y al nuevo administrador asignado
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
        'administradores': administradores 
    })

# Vista de Seguimiento del Ticket
def seguimiento_ticket(request, ticket_id):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')

    ticket = get_object_or_404(Ticket, id=ticket_id)
    usuario = Usuario.objects.get(id=user_id)

    # Verifica si es el propietario o Admin
    if usuario != ticket.usuario and (not usuario.rol or usuario.rol.descripcion != 'ADMIN'):
        messages.error(request, 'No tienes permiso para ver este ticket.')
        return redirect('home')

    if request.method == 'POST':
        comentario_texto = request.POST.get('comentario')
        if comentario_texto:
            # Creación de comentario
            comentario = Comentario.objects.create(ticket=ticket, usuario=usuario, texto=comentario_texto)

            # Genera un mensaje para el Admin
            mensaje_admin = render_to_string('tickets/email_template_admin_comentario.html', {
                'ticket_id': ticket.id,
                'usuario': usuario,
                'tipoCaso': ticket.tipoCaso.descripcion,
                'comentario': comentario.texto,
                'prioridad': ticket.get_prioridad_display(),
            })

            # Genera un mensaje para el usuario
            mensaje_usuario = render_to_string('tickets/email_template_user_comentario.html', {
                'ticket_id': ticket.id,
                'tipoCaso': ticket.tipoCaso.descripcion,
                'comentario': comentario.texto,
                'prioridad': ticket.get_prioridad_display(),
            })

            # Envía correo al Admin
            enviar_correo_admin.delay(
                ticket.id,
                'soporte@altamiragroup.com.py',
                mensaje_admin
            )

            # Envía correo al usuario
            enviar_correo_usuario.delay(
                ticket.id,
                ticket.usuario.email,
                mensaje_usuario
            )

    comentarios = ticket.comentarios.all().order_by('fecha_creacion')
    return render(request, 'tickets/seguimiento_ticket.html', {
        'ticket': ticket,
        'comentarios': comentarios,
    })
