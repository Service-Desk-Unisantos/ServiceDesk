from django.contrib import admin

from .models import Chamado, Comentario


@admin.register(Chamado)
class ChamadoAdmin(admin.ModelAdmin):
    # Campos principais no painel admin para acompanhamento dos chamados.
    list_display = ("id", "titulo", "categoria", "prioridade", "status", "usuario", "data_criacao")
    list_filter = ("categoria", "prioridade", "status", "data_criacao")
    search_fields = ("titulo", "descricao", "usuario__username")
    ordering = ("-data_criacao",)


@admin.register(Comentario)
class ComentarioAdmin(admin.ModelAdmin):
    # Facilita localizar comentarios vinculados aos chamados.
    list_display = ("id", "chamado", "usuario", "data")
    list_filter = ("data",)
    search_fields = ("texto", "usuario__username", "chamado__titulo")
