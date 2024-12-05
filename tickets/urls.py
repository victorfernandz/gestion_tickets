from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login, name='login'),  
    path('home/', views.home, name='home'),  
    path('logout/', views.logout, name='logout'),  
    path('crear_ticket', views.crear_ticket, name='crear_ticket'), 
    path('listar_ticket', views.listar_tickets, name='listar_tickets'),
    path('administrar_tickets', views.administrar_tickets, name='administrar_tickets'),
]
