from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import (
    AtualizacaoChamadoAdminForm,
    CadastroUsuarioForm,
    ChamadoForm,
    LoginUsuarioForm,
)
from .models import Chamado, Comentario


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
        "chamados/login.html",
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

    return render(request, "chamados/cadastro.html", {"form": form})


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
    return render(request, "chamados/criar.html", {"form": form})


@login_required
def lista_chamados(request):
    # Regra de negocio:
    # - staff (tecnico/admin) enxerga todos os chamados no painel
    # - cliente nao recebe lista no painel inicial (usa area de atalhos)
    if request.user.is_staff:
        # Carrega comentarios junto para exibir historico de respostas no modal admin.
        chamados = Chamado.objects.all().prefetch_related("comentarios__usuario")
    else:
        # Evita enviar historico de chamados para o template de painel do cliente.
        chamados = Chamado.objects.none()

    # Envia a lista para o template do painel.
    return render(request, "chamados/lista.html", {"chamados": chamados})


@login_required
def atualizar_chamado_admin(request, chamado_id):
    # Apenas equipe de infra (staff/admin) pode atualizar status, prioridade e resposta.
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Somente a equipe de infra pode atualizar chamados.")
        return redirect("lista_chamados")

    # Recupera o chamado selecionado para atualizar os dados de atendimento.
    chamado = get_object_or_404(Chamado, id=chamado_id)
    if request.method != "POST":
        return redirect("lista_chamados")

    # Valida os dados enviados no formulario de atendimento do modal.
    form = AtualizacaoChamadoAdminForm(request.POST, chamado=chamado)
    if not form.is_valid():
        messages.error(request, "Nao foi possivel atualizar o chamado.")
        return redirect("lista_chamados")

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

    messages.success(request, "Chamado atualizado com sucesso.")
    return redirect("lista_chamados")


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
        "chamados/historico_cliente.html",
        {"chamados": chamados},
    )
