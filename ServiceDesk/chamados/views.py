from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import CadastroUsuarioForm, ChamadoForm
from .models import Chamado


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
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            messages.success(request, "Login realizado com sucesso.")
            return redirect(_destino_pos_login(request))
    else:
        form = AuthenticationForm()

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
    # - staff (tecnico/admin) enxerga todos os chamados
    # - usuario comum enxerga apenas os proprios chamados
    if request.user.is_staff:
        chamados = Chamado.objects.all()
    else:
        chamados = Chamado.objects.filter(usuario=request.user)

    # Envia a lista para o template do painel.
    return render(request, "chamados/lista.html", {"chamados": chamados})
