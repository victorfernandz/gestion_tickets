from django.db import models

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
    usuario = models.CharField(max_length=15, unique=True, blank=False, null=False, default='default_user')
    nombre = models.CharField(max_length=255)
    apellido = models.CharField(max_length=255, blank=True)
    cedula = models.CharField(max_length=10, blank=True)
    departamento = models.ForeignKey(Departamento, on_delete=models.CASCADE)  # Si un departamento se elimina, también los usuarios
    rol = models.ForeignKey(Rol, on_delete=models.CASCADE)
    contrasena = models.CharField(max_length=128) 

    def __str__(self):
        return f"{self.nombre} {self.apellido} ({self.usuario})"

#Tabla de Estados    
class Estado(models.Model):
    id = models.AutoField(primary_key=True)
    descripcion = models.CharField(max_length=10)

    def __str__(self):
        return self.descripcion

#Tabla de Tickets
class Ticket(models.Model):
    id = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.DO_NOTHING)
    asunto = models.CharField(max_length=50)
    descripcion = models.TextField()
    fecha_creacion = models.DateTimeField()
    estado = models.ForeignKey(Estado, on_delete=models.DO_NOTHING, null=False, blank=False)

    def __str__(self):
        return self.id