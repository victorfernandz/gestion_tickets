from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Usuario, Ticket

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

# Vista de Tickets
def crear_tickets(request):
    if request.method == 'POST':
        asunto = request.POST.get('asunto')
        descripcion = request.POST.get('descripcion')
        usuario = Usuario.objects.get(id=request.session.get('user_id'))

        # Crear el ticket
        Ticket.objects.create(asunto=asunto, descripcion=descripcion, usuario=usuario)
        messages.success(request= 'Ticket creado existosamente')
        return redirect('home')
    return render(request, 'tickets/crear_ticket.html')