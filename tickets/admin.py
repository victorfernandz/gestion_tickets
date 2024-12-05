from django.contrib import admin
from .models import Departamento, Rol, Usuario, Casos, Categoria

admin.site.register(Departamento)
admin.site.register(Rol)
admin.site.register(Usuario)
admin.site.register(Casos)
admin.site.register(Categoria)