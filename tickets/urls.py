from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login, name='login'),  # Ruta para iniciar sesión
    path('home/', views.home, name='home'),  # Página principal
    path('logout/', views.logout, name='logout'),  # Cerrar sesión
    path('crear_ticket', views.crear_tickets, name='crea_ticket'), # Creación de Tickets
]
