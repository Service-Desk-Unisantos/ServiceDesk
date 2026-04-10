"""
ASGI config for ServiceDesk project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

# Aponta para o modulo correto de settings apos organizacao da pasta de config.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ConfigDjango.settings')

application = get_asgi_application()
