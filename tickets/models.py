from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.core.validators import EmailValidator

# Tabla de Departamentos
class Departamento(models.Model):
    id = models.AutoField(primary_key=True)
    descripcion = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.descripcion

# Tabla de Roles
class Rol(models.Model):
    id = models.AutoField(primary_key=True)
    descripcion = models.CharField(max_length=50)

    def __str__(self):
        return self.descripcion

# Tabla de Usuarios
class Usuario(models.Model):
    id = models.AutoField(primary_key=True)
    usuario = models.CharField(max_length=20, unique=True, blank=False, null=False, default='default_user')
    email = models.CharField(max_length=50, blank=False, null=False, default='example@altamiragroup.com.py', validators=[EmailValidator(message="Ingrese un correo válido.")])
    nombre = models.CharField(max_length=255)
    apellido = models.CharField(max_length=255, blank=True)
    departamento = models.ForeignKey(Departamento, on_delete=models.CASCADE)
    rol = models.ForeignKey(Rol, on_delete=models.CASCADE)
    contrasena = models.CharField(max_length=128)
    necesita_cambiar_contrasena = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.nombre} {self.apellido} ({self.usuario})"

# Tabla de Categorías
class Categoria(models.Model):
    id = models.AutoField(primary_key=True)
    descripcion = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.id} - {self.descripcion}"

# Tabla Tipo de Casos
class Casos(models.Model):
    id = models.AutoField(primary_key=True)
    descripcion = models.CharField(max_length=50)
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.id} - {self.descripcion}"
    
def ticket_upload_path(instance, filename):
    return f"tickets_adjuntos/{instance.id}/{filename}"

# Tabla de Tickets
class Ticket(models.Model):
    ESTADO = [
        (1, "Abierto"),
        (2, "En proceso"),
        (3, "En espera de feedback"),
        (4, "Cerrado"),
    ]
    PRIORIDAD = [
        (1, "Bajo"),
        (2, "Medio"),
        (3, "Alto"),
        (4, "Muy Alto"),
    ]

    id = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, blank=False, null=False, default=1)
    tipoCaso = models.ForeignKey(Casos, on_delete=models.CASCADE, blank=False, null=False)
    descripcion = models.TextField(max_length=500)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    estado = models.IntegerField(choices=ESTADO, default=1)
    prioridad = models.IntegerField(choices=PRIORIDAD, default=1)
    admin_asignado = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name="tickets_asignados")
    resolucion = models.TextField(blank=True, null=True)  
    horario_asignacion = models.DurationField(null=True, blank=True)  
    tiempo_resolucion = models.DurationField(null=True, blank=True)
    archivo = models.FileField(upload_to=ticket_upload_path, null=True, blank=True)
    
    def __str__(self):
        return f"Ticket {self.id} - {self.tipoCaso.descripcion}"

# Tabla de Comentarios
class Comentario(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="comentarios")  
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE) 
    texto = models.TextField() 
    fecha_creacion = models.DateTimeField(auto_now_add=True)  

    def __str__(self):
        return f"Comentario de {self.usuario} en Ticket {self.ticket.id}"

class ArchivoAdjunto(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="archivos")
    archivo = models.FileField(upload_to="tickets_adjuntos/")
    fecha_subida = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.archivo.name
    
# Restablecimiento de contraseña
class TokenRestablecimiento(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    token = models.CharField(max_length=100, unique=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    usado = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Token para {self.usuario.usuario}"
    
    def esta_activo(self):
        # El token expira después de 24 horas
        return not self.usado and self.fecha_creacion > timezone.now() - timedelta(hours=24)