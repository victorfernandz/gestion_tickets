from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),  # Ruta para la vista de inicio de sesión
]
