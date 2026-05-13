from django.contrib import admin
from django.utils.html import format_html
from .models import Departamento, Rol, Usuario, Casos, Categoria, OpcionCampoAdmin
from tickets.models import Ticket

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario', 'estado', 'fecha_creacion')

@admin.register(OpcionCampoAdmin)
class OpcionCampoAdminAdmin(admin.ModelAdmin):
    list_display = ('id', 'descripcion', 'activo')
    list_editable = ('activo',)
    search_fields = ('descripcion',)

admin.site.register(Departamento)
admin.site.register(Rol)
admin.site.register(Usuario)
admin.site.register(Casos)
admin.site.register(Categoria)