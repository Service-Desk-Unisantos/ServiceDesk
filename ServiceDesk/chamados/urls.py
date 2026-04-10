from django.urls import path

from . import views

urlpatterns = [
    # Tela inicial da aplicacao: lista de chamados (RF04 e RF05).
    path("", views.lista_chamados, name="lista_chamados"),
    # Cadastro e autenticacao de usuarios (RF01 e RF02).
    path("cadastro/", views.cadastro_usuario, name="cadastro_usuario"),
    path("login/", views.login_usuario, name="login_usuario"),
    path("logout/", views.logout_usuario, name="logout_usuario"),
    # Registro de novos chamados (RF03).
    path("novo/", views.criar_chamado, name="criar_chamado"),
    # Atualizacao operacional de chamado para equipe de infra.
    path(
        "chamado/<int:chamado_id>/atualizar/",
        views.atualizar_chamado_admin,
        name="atualizar_chamado_admin",
    ),
    # Historico individual de chamados para perfil cliente.
    path(
        "meus-chamados/",
        views.historico_chamados_cliente,
        name="historico_chamados_cliente",
    ),
]
