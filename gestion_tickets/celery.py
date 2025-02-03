from __future__ import absolute_import, unicode_literals
import os
import logging
from celery import Celery

# Configuración de Django para Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_tickets.settings')

app = Celery('gestion_tickets')

# Configurar Celery para leer las configuraciones desde settings.py
app.config_from_object('django.conf:settings', namespace='CELERY')

# Zona horaria correcta
app.conf.timezone = 'America/Asuncion'

# Auto-descubre tareas en las aplicaciones instaladas de Django
app.autodiscover_tasks()

# Configuración de LOGGING para Celery
logger = logging.getLogger('celery')
logger.setLevel(logging.INFO)

# Formato de logs
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Guardar logs en un archivo
log_file = "/var/log/celery/celery.log"  # Ruta donde se guardarán los logs
file_handler = logging.FileHandler(log_file)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Loggear errores en consola
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

@app.task(bind=True)
def debug_task(self):
    logger.info(f'Debug Task ejecutada: {self.request!r}')
