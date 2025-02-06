from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('login/', views.login, name='login'),  
    path('home/', views.home, name='home'),  
    path('logout/', views.logout, name='logout'),  
    path('crear_ticket/', views.crear_ticket, name='crear_ticket'), 
    path('listar_tickets/', views.listar_tickets, name='listar_tickets'),
    path('administrar_tickets/', views.administrar_tickets, name='administrar_tickets'),
    path('seguimiento/<int:ticket_id>/', views.seguimiento_ticket, name='seguimiento_ticket'),
    path('cambiar_contrasena/<int:user_id>/', views.cambiar_contrasena, name='cambiar_contrasena'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)