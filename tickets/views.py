from django.shortcuts import render, redirect, get_object_or_404
from django.utils.crypto import get_random_string
from django.contrib import messages
from .models import Usuario, Ticket, Casos, Categoria, Comentario, ArchivoAdjunto, TokenRestablecimiento,Departamento
from django.template.loader import render_to_string
from django.http import JsonResponse
from datetime import timedelta
from django.contrib.auth.hashers import make_password, check_password
from .tasks import (enviar_correo_admin, enviar_correo_usuario)
from django.core.paginator import Paginator
from django.urls import reverse
from django.utils.dateparse import parse_date
from datetime import datetime
from django.utils import timezone  


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

    usuario_logueado = Usuario.objects.get(id=user_id)

    # Si es una petición AJAX para filtrar casos por categoría
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        categoria_id = request.GET.get('categoria_id')
        if categoria_id:
            if categoria_id == '4':
                casos = Casos.objects.filter(categoria=4)
            elif categoria_id == '3':
                casos = Casos.objects.filter(categoria=3)
            elif categoria_id == '2':
                casos = Casos.objects.filter(categoria=2)
            elif categoria_id == '1':
                casos = Casos.objects.filter(categoria=1)
            else:
                casos = Casos.objects.exclude(categoria=4)
            
            data = {
                'casos': [{'id': c.id, 'descripcion': c.descripcion} for c in casos]
            }
            return JsonResponse(data)
        else:
            return JsonResponse({'casos': []})

    if request.method == 'POST':

        tipo_caso_id = request.POST.get('tipoCaso')
        descripcion = request.POST.get('descripcion')
        prioridad = request.POST.get('prioridad')
        categoria_id = request.POST.get('categoria')
        usuario_destino_id = request.POST.get('usuario_destino') 

        if not tipo_caso_id or not descripcion or not categoria_id:
            messages.error(request, 'Todos los campos son obligatorios.')
        else:
            tipo_caso = Casos.objects.get(id=tipo_caso_id)
            categoria = Categoria.objects.get(id=categoria_id)

            # Para quién es el ticket?
            if usuario_destino_id:
                usuario_afectado = Usuario.objects.get(id=usuario_destino_id)
            else:
                usuario_afectado = usuario_logueado
            ticket = Ticket.objects.create(
                categoria=categoria,
                usuario=usuario_afectado,     
                creador=usuario_logueado,   
                tipoCaso=tipo_caso,
                descripcion=descripcion,
                estado=1,
                prioridad=prioridad,
            )

            # Generar los mensajes para los correos
            prioridad_descripcion = ticket.get_prioridad_display()
            mensaje_admin = render_to_string('tickets/email_template.html', {
                'ticket_id': ticket.id,
                'usuario': usuario_afectado, 
                'tipoCaso': tipo_caso.descripcion,
                'descripcion': descripcion,
                'prioridad': prioridad_descripcion,#ticket.get_prioridad_display(),
            })

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
                'prioridad': prioridad_descripcion#ticket.get_prioridad_display(),
            })            

            #correo al usuario afectado (no siempre el que crea)
            enviar_correo_usuario.delay(
                ticket.id, 
                usuario_afectado.email, 
                mensaje_usuario,
                'No responda este correo - Se ha creado un nuevo ticket'
            )

            return redirect('listar_tickets')

    # GET normal: mostrar formulario
    tipo_categoria = Categoria.objects.all()
    usuarios = Usuario.objects.all().order_by('apellido', 'nombre')

    return render(request, 'tickets/crear_ticket.html', {
        'tipo_categoria': tipo_categoria,
        'usuarios': usuarios,
        'usuario_logueado': usuario_logueado,
    })
  
# Vista para listar tickets
def listar_tickets(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login') 

    usuario = Usuario.objects.get(id=user_id)

    # Verificamos el rol para filtrar los tickets
    if usuario.rol.descripcion != 'ADMIN':
        tickets_list = Ticket.objects.filter(usuario_id=user_id).order_by('-fecha_creacion')
    else:
        tickets_list = Ticket.objects.all().order_by('id')

    #paginador
    paginador = Paginator(tickets_list, 10)  # 10 tickets por página 
    nro_pagina = request.GET.get('pagina')
    tickets = paginador.get_page(nro_pagina)

    return render(request, 'tickets/listar_tickets.html', {
        'tickets': tickets
    })

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
    departamentos = Departamento.objects.all()
    usuarios = Usuario.objects.all().order_by('nombre') 
    
    
    #Mantener otros parámetros de filtro en la paginación
    params = request.GET.copy()
    params.pop('pagina', None)
    querystring = params.urlencode()    
    #------------------------------------------------------
    

    portal_url = "http://192.168.0.25"

    # Filtros
    filtro_estado = request.GET.get('estado', '')
    filtro_prioridad = request.GET.get('prioridad', '')
    filtro_admin = request.GET.get('admin_asignado', '')
    filtro_categoria = request.GET.get('categoria', '')

    #filtro por departamento
    filtro_departamento = request.GET.get('departamento')
    #Filtro usuarios
    filtro_usuario = request.GET.get('usuario')
    #Filtros por rango de fechas
    filtro_fecha_desde = request.GET.get('fecha_desde')
    filtro_fecha_hasta = request.GET.get('fecha_hasta')
    #lista base de usuarios para el select
    
    if filtro_departamento:
     usuarios = usuarios.filter(departamento_id=filtro_departamento)
     tickets_list = tickets_list.filter(usuario__departamento_id=filtro_departamento) 
    #if filtro_departamento:
     #tickets_list = tickets_list.filter( usuario__departamento_id=filtro_departamento)   
    if filtro_usuario:
     tickets_list = tickets_list.filter(usuario_id=filtro_usuario)

    if filtro_estado:
        tickets_list = tickets_list.filter(estado=filtro_estado)

    if filtro_prioridad:
        tickets_list = tickets_list.filter(prioridad=filtro_prioridad)
    #filtro antiguo        
   # if filtro_fecha:
       # tickets_list = tickets_list.filter(fecha_creacion__date=filtro_fecha)
    from datetime import datetime

# Validación de rango de fechas
    if filtro_fecha_desde and filtro_fecha_hasta:
        try:
            fecha_desde_dt = datetime.strptime(filtro_fecha_desde, "%Y-%m-%d").date()
            fecha_hasta_dt = datetime.strptime(filtro_fecha_hasta, "%Y-%m-%d").date()

            if fecha_hasta_dt < fecha_desde_dt:
                messages.error(request, "La fecha HASTA no puede ser menor que la fecha DESDE.")
            else:
                tickets_list = tickets_list.filter(fecha_creacion__date__range=[fecha_desde_dt, fecha_hasta_dt])

        except ValueError:
            messages.error(request, "Formato de fecha inválido.")

    if filtro_admin:
        tickets_list = tickets_list.filter(admin_asignado_id=filtro_admin)
    if filtro_categoria:
        tickets_list = tickets_list.filter(categoria_id=filtro_categoria)

    # Aplica paginación
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
        #nuevo_tiempo_resolucion = request.POST.get('tiempo_resolucion', '')
        nuevo_tiempo_resolucion = request.POST.get('fecha_hora_resolucion', '')
        

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
                ticket.fecha_hora_resolucion = timedelta(hours=horas, minutes=minutos)
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
        'departamentos': departamentos,
        'usuarios': usuarios,
        'querystring': querystring,
    })

# Vista de Seguimiento del Ticket
def seguimiento_ticket(request, ticket_id):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')

    ticket = get_object_or_404(Ticket, id=ticket_id)
    usuario = Usuario.objects.get(id=user_id)

    # Es admin?
    es_admin = usuario.rol and usuario.rol.descripcion == 'ADMIN'

    # Verifica si es el propietario o Admin
    if usuario != ticket.usuario and not es_admin:
        messages.error(request, 'No tienes permiso para ver este ticket.')
        return redirect('home')

    if request.method == 'POST':

        # FORM DEL SIDEBAR (estado, prioridad, agente, tipo, categoría, fecha)
        if 'fecha_hora_resolucion' in request.POST:

            # 🚫 SOLO ADMIN PUEDE EDITAR ESTO
            if not es_admin:
                messages.error(request, 'No tienes permiso para editar la información del ticket.')
                return redirect('seguimiento_ticket', ticket_id=ticket.id)

            nuevo_estado = request.POST.get('nuevo_estado')
            nueva_prioridad = request.POST.get('nueva_prioridad') 
            fecha_hora_res_str = request.POST.get('fecha_hora_resolucion')
            nuevo_admin_id = request.POST.get('nuevo_admin')
            nueva_categoria_id = request.POST.get('nueva_categoria')
            nuevo_tipo_caso_id = request.POST.get('nuevo_tipo_caso')
            horario_asignacion_str = request.POST.get('tiempo_fecha_asignacion')


            
            # Guarda tiempo y hora de asignación
            if horario_asignacion_str:
                try:
                    tr = datetime.fromisoformat(horario_asignacion_str)
                    tr_aware = timezone.make_aware(tr)
                    ticket.tiempo_fecha_asignacion = tr_aware
                    # Guardar solo HH:MM como duración
                    ticket.horario_asignacion = timedelta(hours=tr.hour, minutes=tr.minute)
                   # horas, minutos = map(int, horario_asignacion_str.split(':'))
                   # ticket.horario_asignacion = timedelta(hours=horas, minutes=minutos)
                except ValueError:
                    messages.error(request, "Formato inválido en horario de asignación.")
                    return redirect('seguimiento_ticket', ticket_id=ticket.id)
            else:
                ticket.tiempo_fecha_asignacion = None
                ticket.horario_asignacion = None
                    

            # Actualizar estado
            if nuevo_estado:
                ticket.estado = int(nuevo_estado)
            #Nueva Prioridad
            if nueva_prioridad:
                ticket.prioridad = (nueva_prioridad)
            # Actualizar administrador asignado    
            if nuevo_admin_id:
                ticket.admin_asignado = Usuario.objects.get(id=nuevo_admin_id)
            else:
                ticket.admin_asignado = None

            # Actualizar tipo de caso
            if nuevo_tipo_caso_id:
                ticket.tipoCaso = Casos.objects.get(id=nuevo_tipo_caso_id)

            # Actualizar categoría
            if nueva_categoria_id:
                ticket.categoria = Categoria.objects.get(id=nueva_categoria_id)

            # Guardar fecha y hora de resolución
            if fecha_hora_res_str:
                try:
                    dt = datetime.fromisoformat(fecha_hora_res_str)
                    dt_aware = timezone.make_aware(dt)
                    ticket.fecha_hora_resolucion = dt_aware
                    # Guardar solo HH:MM como duración
                    ticket.tiempo_resolucion = timedelta(hours=dt.hour, minutes=dt.minute)
                except ValueError:
                    messages.error(request, "Formato inválido en fecha y hora.")
                    return redirect('seguimiento_ticket', ticket_id=ticket.id)
            else:
                ticket.fecha_hora_resolucion = None
                ticket.tiempo_resolucion = None

            ticket.save()
            messages.success(request, "Información del ticket actualizada correctamente.")
            return redirect('seguimiento_ticket', ticket_id=ticket.id)

        # =============================================
        # 👉 ESTE ES EL FORM DE COMENTARIOS Y ARCHIVOS
        # =============================================
        comentario_texto = request.POST.get('comentario')
        archivo = request.FILES.get('archivo')

        portal_url = "http://192.168.0.25"
        ticket_url = f"{portal_url}{reverse('seguimiento_ticket', args=[ticket.id])}"

        usuario_data = {
            'id': usuario.id,
            'nombre': usuario.nombre,
            'apellido': usuario.apellido,
            'email': usuario.email
        }

        admin_email = ticket.admin_asignado.email if ticket.admin_asignado else "soporte@altamiragroup.com.py"

        # Guardar comentario
        if comentario_texto:
            comentario = Comentario.objects.create(ticket=ticket, usuario=usuario, texto=comentario_texto)

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

        # Guardar archivo adjunto
        if archivo:
            archivo_adjunto = ArchivoAdjunto.objects.create(ticket=ticket, archivo=archivo)

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

    # GET: datos para mostrar
    comentarios = ticket.comentarios.all().order_by('fecha_creacion')
    archivos = ticket.archivos.all()
    administradores = Usuario.objects.filter(rol__descripcion='ADMIN')
    categorias = Categoria.objects.all()
    tipos_caso = Casos.objects.all()

    return render(request, 'tickets/seguimiento_ticket.html', {
        'ticket': ticket,
        'comentarios': comentarios,
        'archivos': archivos,
        'categorias': categorias,
        'tipos_caso': tipos_caso,
        'administradores': administradores,
        'es_admin': es_admin,   # para mostrar/ocultar secciones
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
#def actualizar_ticket(request, ticket_id):