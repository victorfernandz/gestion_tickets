from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# Configuración para usar el archivo settings.py de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_tickets.settings')

app = Celery('gestion_tickets')

# Lee la configuración de Celery desde settings.py con el prefijo CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-descubre tareas definidas en aplicaciones instaladas
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')


app.conf.update(
    task_annotations={
        'tickets.tasks.enviar_correo': {'rate_limit': '10/m'}
    },
    task_default_retry_delay=300,  # Retraso entre reintentos (5 minutos)
    task_max_retries=5,  # Máximo de reintentos
)
