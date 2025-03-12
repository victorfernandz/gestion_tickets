from django.shortcuts import render, redirect, get_object_or_404
from django.utils.crypto import get_random_string
from django.contrib import messages
from .models import Usuario, Ticket, Casos, Categoria, Comentario, ArchivoAdjunto, TokenRestablecimiento
from django.template.loader import render_to_string
from django.http import JsonResponse
from datetime import timedelta
from django.contrib.auth.hashers import make_password, check_password
from .tasks import (enviar_correo_admin, enviar_correo_usuario)
from django.core.paginator import Paginator
from django.urls import reverse

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

    if request.method == 'POST':
        tipo_caso_id = request.POST.get('tipoCaso')
        descripcion = request.POST.get('descripcion')
        prioridad = request.POST.get('prioridad')
        categoria_id = request.POST.get('categoria')
#        archivo = request.FILES.get("archivo")

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
                prioridad=prioridad,
            )

            # Guardar archivo si se adjuntó
            #if archivo:
            #    ArchivoAdjunto.objects.create(ticket=ticket, archivo=archivo)

            # Generar los mensajes para los correos
            mensaje_admin = render_to_string('tickets/email_template.html', {
                'ticket_id': ticket.id,
                'usuario': usuario, 
                'tipoCaso': tipo_caso.descripcion,
                'descripcion': descripcion,
                'prioridad': ticket.get_prioridad_display(),
            })

            # Delegar el envío de correos a Celery
            enviar_correo_admin.delay(
                ticket.id, 
                'soporte@altamiragroup.com.py',
                mensaje_admin,
                'No responda este correo - Se ha creado un nuevo ticket'
            )

            mensaje_usuario = render_to_string('tickets/email_template_user.html', {
                'ticket_id': ticket.id,
                'tipoCaso': tipo_caso.descripcion,
                'descripcion': descripcion,
                'prioridad': ticket.get_prioridad_display(),
            })            

            enviar_correo_usuario.delay(
                ticket.id, 
                usuario.email, 
                mensaje_usuario,
                'No responda este correo - Se ha creado un nuevo ticket'
            )

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
    usuario = get_object_or_404(Usuario, id=user_id)
    if usuario.rol.descripcion != 'ADMIN':
        return redirect('home')

    # Obtener todos los tickets ordenados por fecha de creación
    tickets_list = Ticket.objects.all().order_by('fecha_creacion')

    administradores = Usuario.objects.filter(rol__descripcion='ADMIN')
    categorias = Categoria.objects.all()

    portal_url = "http://192.168.0.25"

    # Filtros
    filtro_estado = request.GET.get('estado', '')
    filtro_prioridad = request.GET.get('prioridad', '')
    filtro_fecha = request.GET.get('fecha', '')
    filtro_admin = request.GET.get('admin_asignado', '')
    filtro_categoria = request.GET.get('categoria', '')

    if filtro_estado:
        tickets_list = tickets_list.filter(estado=filtro_estado)
    if filtro_prioridad:
        tickets_list = tickets_list.filter(prioridad=filtro_prioridad)
    if filtro_fecha:
        tickets_list = tickets_list.filter(fecha_creacion__date=filtro_fecha)
    if filtro_admin:
        tickets_list = tickets_list.filter(admin_asignado_id=filtro_admin)
    if filtro_categoria:
        tickets_list = tickets_list.filter(categoria_id=filtro_categoria)

    # Aplica paginación después de los filtros
    paginador = Paginator(tickets_list, 10)  # 10 tickets por página
    nro_pagina = request.GET.get('pagina')
    tickets = paginador.get_page(nro_pagina)

    # Procesar la actualización de un ticket
    if request.method == 'POST':
        ticket_id = request.POST.get('ticket_id', '')                                                                                                                       
        nuevo_estado = request.POST.get('nuevo_estado', '')
        nueva_prioridad = request.POST.get('nueva_prioridad', '')
        nuevo_admin_id = request.POST.get('nuevo_admin', '')
        nuevo_horario_asignacion = request.POST.get('horario_asignacion', '')
        nuevo_tiempo_resolucion = request.POST.get('tiempo_resolucion', '')

        ticket = get_object_or_404(Ticket, id=ticket_id)

        ticket_url = f"{portal_url}{reverse('seguimiento_ticket', args=[ticket.id])}"

        # Actualiza la hora de asignación
        if nuevo_horario_asignacion:
            try:
                horas, minutos = map(int, nuevo_horario_asignacion.split(':'))
                ticket.horario_asignacion = timedelta(hours=horas, minutes=minutos)
            except ValueError:
                messages.error(request, 'Formato de horario de asignación inválido. Use HH:MM.')
                return redirect('administrar_tickets')

        # Procesar tiempo de resolución
        if nuevo_tiempo_resolucion:
            try:
                horas, minutos = map(int, nuevo_tiempo_resolucion.split(':'))
                ticket.tiempo_resolucion = timedelta(hours=horas, minutes=minutos)
            except ValueError:
                messages.error(request, 'Formato inválido para tiempo de resolución. Use HH:MM.')
                return redirect('administrar_tickets')

        # Actualiza estado, prioridad y administrador si se proporcionan
        if nuevo_estado:
            ticket.estado = nuevo_estado
        if nueva_prioridad:
            ticket.prioridad = nueva_prioridad
        if nuevo_admin_id:
            nuevo_admin = get_object_or_404(Usuario, id=nuevo_admin_id)
            ticket.admin_asignado = nuevo_admin

        ticket.save()

        # REFRESCAR el objeto para asegurar que Django reconozca los valores como choices
        ticket.refresh_from_db()

        # Obtener la descripción del estado y la prioridad
        estado_descripcion = ticket.get_estado_display()
        prioridad_descripcion = ticket.get_prioridad_display()

        if nuevo_estado:
            mensaje_usuario = render_to_string('tickets/email_actualizacion_estado_user.html', {
                'ticket': ticket,
                'horario': nuevo_horario_asignacion,
                'estado' : estado_descripcion,
                'prioridad' : prioridad_descripcion,
                'ticket_url' : ticket_url,
            })

            enviar_correo_usuario.delay(
                ticket.id,
                ticket.usuario.email,
                mensaje_usuario,
                'No responda este correo - Se ha actualizado su ticket'
            )

        # Enviar correos si se asignó un administrador y horario de asignación
        if ticket.admin_asignado and nuevo_horario_asignacion:
            mensaje_admin = render_to_string('tickets/email_actualizacion_admin.html', {
                'ticket': ticket,
                'horario': nuevo_horario_asignacion,
                'estado' : estado_descripcion,
                'prioridad' : prioridad_descripcion,
                'admin_usuario': usuario,
                'ticket_url' : ticket_url,
            })

            enviar_correo_admin.delay(
                ticket.id,
                ticket.admin_asignado.email,
                mensaje_admin,
                'Se le ha asignado el ticket'
            )

            mensaje_usuario = render_to_string('tickets/email_actualizacion_user.html', {
                'ticket': ticket,
                'horario': nuevo_horario_asignacion,
                'estado' : estado_descripcion,
                'prioridad' : prioridad_descripcion,
                'ticket_url' : ticket_url,
            })

            enviar_correo_usuario.delay(
                ticket.id,
                ticket.usuario.email,
                mensaje_usuario,
                'No responda este correo - Se ha actualizado su ticket'
            )

        return redirect('administrar_tickets')

    return render(request, 'tickets/administrar_tickets.html', {
        'tickets': tickets,
        'administradores': administradores,
        'categorias': categorias,
        'estado_seleccionado': filtro_estado,
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
        archivo = request.FILES.get('archivo')

        # Generar URL del ticket 
        portal_url = "http://192.168.0.25"
        ticket_url = f"{portal_url}{reverse('seguimiento_ticket', args=[ticket.id])}"

        # Extraer datos serializables del usuario
        usuario_data = {
            'id': usuario.id,
            'nombre': usuario.nombre,
            'apellido': usuario.apellido,
            'email': usuario.email
        }

        # Obtener el correo del administrador asignado al ticket
        admin_email = ticket.admin_asignado.email if ticket.admin_asignado else "soporte@altamiragroup.com.py"

        # Manejo de comentarios
        if comentario_texto:
            comentario = Comentario.objects.create(ticket=ticket, usuario=usuario, texto=comentario_texto)

            # Enviar correos
            mensaje_admin = render_to_string('tickets/email_template_admin_comentario.html', {
                'ticket_id': ticket.id,
                'usuario': usuario_data,
                'tipoCaso': ticket.tipoCaso.descripcion,
                'comentario': comentario.texto,
                'prioridad': ticket.get_prioridad_display(),
                'ticket_url': ticket_url,
            })

            enviar_correo_admin.delay(ticket.id, admin_email, mensaje_admin, 'Se ha actualizado su ticket')
            
            mensaje_usuario = render_to_string('tickets/email_template_user_comentario.html', {
                'ticket_id': ticket.id,
                'usuario': usuario_data,
                'tipoCaso': ticket.tipoCaso.descripcion,
                'comentario': comentario.texto,
                'prioridad': ticket.get_prioridad_display(),
                'ticket_url': ticket_url,
            })
            
            enviar_correo_usuario.delay(ticket.id, ticket.usuario.email, mensaje_usuario, 'No responda este correo - Se ha actualizado su ticket')

        # Manejo de subida de archivos
        if archivo:
            archivo_adjunto = ArchivoAdjunto.objects.create(ticket=ticket, archivo=archivo)

            # Enviar correos para el archivo adjunto
            mensaje_archivo = render_to_string('tickets/email_template_admin_comentario.html', {
                'ticket_id': ticket.id,
                'usuario': usuario_data,
                'tipoCaso': ticket.tipoCaso.descripcion,
                'archivo': archivo_adjunto.archivo.name,
                'ticket_url': ticket_url,
            })

            enviar_correo_admin.delay(ticket.id, admin_email, mensaje_archivo, 'Se ha actualizado su ticket')

        if not comentario_texto and not archivo:
            messages.error(request, "Debe agregar un comentario o un archivo.")
            return redirect('seguimiento_ticket', ticket_id=ticket.id)

        return redirect('seguimiento_ticket', ticket_id=ticket.id)

    comentarios = ticket.comentarios.all().order_by('fecha_creacion')
    archivos = ticket.archivos.all()  # Obtener archivos adjuntos

    return render(request, 'tickets/seguimiento_ticket.html', {
        'ticket': ticket,
        'comentarios': comentarios,
        'archivos': archivos,
    })

# Restablecer contraseña
from django.utils.crypto import get_random_string

def solicitar_restablecer_contrasena(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            usuario = Usuario.objects.get(email=email)
            
            # Crear un token único
            token = get_random_string(length=50)
            TokenRestablecimiento.objects.create(
                usuario=usuario,
                token=token
            )
            
            # URL para restablecer contraseña
            reset_url = request.build_absolute_uri(
                reverse('restablecer_contrasena', args=[token])
            )
            
            # Preparar correo
            mensaje_html = render_to_string('tickets/email_reset_password.html', {
                'usuario': usuario,
                'reset_url': reset_url
            })
            
            # Enviar correo
            enviar_correo_usuario.delay(
                0,  # No hay ticket asociado
                usuario.email,
                mensaje_html,
                'Restablecimiento de contraseña'
            )
            
            messages.success(request, 'Se ha enviado un correo con instrucciones para restablecer tu contraseña.')
            return redirect('login')
            
        except Usuario.DoesNotExist:
            messages.success(request, 'Si el correo existe en nuestro sistema, recibirás instrucciones para restablecer tu contraseña.')
            return redirect('login')
    
    return render(request, 'tickets/solicitar_reset.html')

def restablecer_contrasena(request, token):
    try:
        token_obj = TokenRestablecimiento.objects.get(token=token)
        
        # Verificar si el token es válido
        if not token_obj.esta_activo():
            messages.error(request, 'El enlace para restablecer la contraseña ha expirado.')
            return redirect('login')
        
        usuario = token_obj.usuario
        
        if request.method == 'POST':
            nueva_contrasena = request.POST.get('nueva_contrasena')
            confirmar_contrasena = request.POST.get('confirmar_contrasena')
            
            if nueva_contrasena != confirmar_contrasena:
                messages.error(request, 'Las contraseñas no coinciden.')
                return render(request, 'tickets/restablecer_contrasena.html')
            
            # Actualizar contraseña
            usuario.contrasena = make_password(nueva_contrasena)
            usuario.necesita_cambiar_contrasena = False
            usuario.save()
            
            # Marcar token como usado
            token_obj.usado = True
            token_obj.save()
            
            messages.success(request, 'Tu contraseña ha sido restablecida exitosamente. Ya puedes iniciar sesión.')
            return redirect('login')
        
        return render(request, 'tickets/restablecer_contrasena.html', {'token': token})
        
    except TokenRestablecimiento.DoesNotExist:
        messages.error(request, 'El enlace para restablecer la contraseña no es válido.')
        return redirect('login')
