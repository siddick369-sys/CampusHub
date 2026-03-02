# config/celery.py (adapte le nom 'config' à ton projet)
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CampuHub.settings')  

app = Celery('CampuHub')  # le nom peut être celui de ton projet

app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()