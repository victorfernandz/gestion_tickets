from django.contrib import admin
from django.utils.html import format_html
from .models import Departamento, Rol, Usuario, Casos, Categoria
from tickets.models import Ticket

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario', 'estado', 'fecha_creacion', 'ultimo_error')

    def ultimo_error(self, obj):
        if obj.error_envio:
            return format_html(f"<span style='color:red;'>{obj.error_envio}</span>")
        return "Sin errores"

admin.site.register(Departamento)
admin.site.register(Rol)
admin.site.register(Usuario)
admin.site.register(Casos)
admin.site.register(Categoria)