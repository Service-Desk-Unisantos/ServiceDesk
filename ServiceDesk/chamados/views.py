from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import (
    AtualizacaoChamadoAdminForm,
    CadastroUsuarioForm,
    ChamadoForm,
    LoginUsuarioForm,
)
from .models import Chamado, Comentario

import json
import logging


# Logger simples para registrar falhas nao bloqueantes de notificacao.
logger = logging.getLogger(__name__)


def _destino_pos_login(request):
    # Evita redirecionamento para URL externa apos login.
    destino = request.POST.get("next") or request.GET.get("next")
    if destino and url_has_allowed_host_and_scheme(
        url=destino,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return destino
    return "lista_chamados"


def enviar_notificacao_status_chamado(chamado):
    # Monta mensagem simples no formato solicitado para notificacao em tempo real.
    mensagem = (
        f"Seu chamado #{chamado.id} foi atualizado para "
        f"{chamado.get_status_display().upper()}"
    )
    payload = {
        "tipo": "status_chamado",
        "chamado_id": chamado.id,
        "usuario_id": chamado.usuario_id,
        "status": chamado.status,
        "mensagem": mensagem,
    }

    # Import local evita quebrar o Django caso a lib websocket nao esteja instalada.
    try:
        from websockets.sync.client import connect
    except Exception as exc:
        logger.info(
            "Biblioteca websockets indisponivel; notificacao nao enviada. Erro: %s",
            exc,
        )
        return

    # Envia a notificacao para o servidor socket separado do Django.
    try:
        with connect(settings.SOCKET_NOTIFICACAO_URL, open_timeout=0.5) as websocket:
            websocket.send(json.dumps(payload, ensure_ascii=False))
    except Exception as exc:
        logger.info(
            "Falha ao enviar notificacao para o servidor socket: %s",
            exc,
        )


def login_usuario(request):
    # Se ja estiver autenticado, volta direto para o painel.
    if request.user.is_authenticated:
        return redirect("lista_chamados")

    if request.method == "POST":
        # AuthenticationForm valida usuario e senha usando o auth do Django (RF02).
        form = LoginUsuarioForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            messages.success(request, "Login realizado com sucesso.")
            return redirect(_destino_pos_login(request))
    else:
        form = LoginUsuarioForm()

    return render(
        request,
        # Template organizado por pasta da rota de login.
        "chamados/login/index.html",
        {"form": form, "next": request.GET.get("next", "")},
    )


def cadastro_usuario(request):
    # Se ja estiver logado, nao precisa cadastrar de novo.
    if request.user.is_authenticated:
        return redirect("lista_chamados")

    if request.method == "POST":
        # Formulario de cadastro do novo usuario (RF01).
        form = CadastroUsuarioForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            # Login automatico apos cadastro para melhorar a experiencia.
            login(request, usuario)
            messages.success(request, "Cadastro realizado com sucesso.")
            return redirect("lista_chamados")
    else:
        form = CadastroUsuarioForm()

    # Template organizado por pasta da rota de cadastro.
    return render(request, "chamados/cadastro/index.html", {"form": form})


@login_required
def logout_usuario(request):
    # Encerra a sessao do usuario atual.
    logout(request)
    messages.info(request, "Sessao encerrada.")
    return redirect("login_usuario")


@login_required
def criar_chamado(request):
    # Fluxo de criacao do chamado:
    # - GET: exibe formulario vazio
    # - POST: valida dados e salva no banco
    if request.method == "POST":
        form = ChamadoForm(request.POST)
        if form.is_valid():
            # commit=False permite complementar campos antes de salvar.
            chamado = form.save(commit=False)
            # Vincula o chamado ao usuario autenticado.
            chamado.usuario = request.user
            chamado.save()
            messages.success(request, "Chamado registrado com sucesso.")
            # Depois de salvar, volta para o painel principal.
            return redirect("lista_chamados")
    else:
        # Primeira abertura da pagina (sem envio de dados).
        form = ChamadoForm()

    # Renderiza a pagina de abertura de chamado.
    # Template organizado por pasta da rota de novo chamado.
    return render(request, "chamados/novo/index.html", {"form": form})


@login_required
def lista_chamados(request):
    # Regra de negocio:
    # - staff (tecnico/admin) enxerga todos os chamados no painel
    # - cliente nao recebe lista no painel inicial (usa area de atalhos)
    if request.user.is_staff:
        # Lista geral de chamados para acompanhamento inicial do time de infra.
        chamados = Chamado.objects.all()
    else:
        # Evita enviar historico de chamados para o template de painel do cliente.
        chamados = Chamado.objects.none()

    # Envia a lista para o template do painel.
    # Template organizado por pasta da rota principal do painel.
    return render(request, "chamados/lista/index.html", {"chamados": chamados})


@login_required
def detalhe_chamado_admin(request, chamado_id):
    # Apenas equipe de infra (staff/admin) pode acessar o detalhe operacional do chamado.
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Somente a equipe de infra pode visualizar este chamado.")
        return redirect("lista_chamados")

    # Busca o chamado com comentarios e usuario para exibir historico completo na tela dedicada.
    chamado = get_object_or_404(
        Chamado.objects.select_related("usuario").prefetch_related("comentarios__usuario"),
        id=chamado_id,
    )
    # Formulario inicial para atualizar status/prioridade e responder o chamado.
    form_atualizacao = AtualizacaoChamadoAdminForm(chamado=chamado)
    return render(
        request,
        # Template organizado por pasta da rota de detalhe do chamado.
        "chamados/detalhe_chamado/index.html",
        {"chamado": chamado, "form_atualizacao": form_atualizacao},
    )


@login_required
def atualizar_chamado_admin(request, chamado_id):
    # Apenas equipe de infra (staff/admin) pode atualizar status, prioridade e resposta.
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Somente a equipe de infra pode atualizar chamados.")
        return redirect("lista_chamados")

    # Recupera o chamado selecionado para atualizar os dados de atendimento.
    chamado = get_object_or_404(Chamado, id=chamado_id)
    if request.method != "POST":
        return redirect("detalhe_chamado_admin", chamado_id=chamado.id)

    # Valida os dados enviados no formulario de atendimento da tela de detalhe.
    form = AtualizacaoChamadoAdminForm(request.POST, chamado=chamado)
    if not form.is_valid():
        messages.error(request, "Nao foi possivel atualizar o chamado.")
        return redirect("detalhe_chamado_admin", chamado_id=chamado.id)

    # Guarda status anterior para notificar somente quando houver mudanca real.
    status_anterior = chamado.status

    # Salva as alteracoes operacionais feitas pela equipe de infra.
    chamado.status = form.cleaned_data["status"]
    chamado.prioridade = form.cleaned_data["prioridade"]
    chamado.save(update_fields=["status", "prioridade"])

    # Registra resposta textual no historico quando preenchida.
    resposta = form.cleaned_data["resposta"].strip()
    if resposta:
        Comentario.objects.create(
            chamado=chamado,
            usuario=request.user,
            texto=resposta,
        )

    # Dispara notificacao em tempo real para o usuario dono do chamado.
    if status_anterior != chamado.status:
        enviar_notificacao_status_chamado(chamado)

    messages.success(request, "Chamado atualizado com sucesso.")
    return redirect("detalhe_chamado_admin", chamado_id=chamado.id)


@login_required
def historico_chamados_cliente(request):
    # Esta tela foi criada para o perfil cliente consultar somente os proprios chamados.
    if request.user.is_staff or request.user.is_superuser:
        # Perfil admin continua no painel principal de acompanhamento geral.
        messages.info(
            request,
            "O historico individual e destinado ao perfil cliente.",
        )
        return redirect("lista_chamados")

    # Filtro de seguranca: retorna apenas os chamados do usuario autenticado.
    chamados = Chamado.objects.filter(usuario=request.user)
    # Renderiza a nova pagina de historico individual.
    return render(
        request,
        # Template organizado por pasta da rota de historico do cliente.
        "chamados/meus_chamados/index.html",
        {"chamados": chamados},
    )
