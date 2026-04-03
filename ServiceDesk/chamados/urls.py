from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_chamados, name='lista_chamados'),
    path('novo/', views.criar_chamado, name='criar_chamado'),
]