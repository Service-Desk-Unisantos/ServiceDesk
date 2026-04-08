from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import ChamadoForm
from .models import Chamado


@login_required
def criar_chamado(request):
    # Fluxo de criacao do chamado:
    # - GET: exibe formulario vazio
    # - POST: valida dados e salva no banco
    if request.method == "POST":
        # Monta o formulario com os dados enviados pela tela.
        form = ChamadoForm(request.POST)
        if form.is_valid():
            # commit=False permite complementar campos antes de salvar.
            chamado = form.save(commit=False)
            # Vincula o chamado ao usuario autenticado.
            chamado.usuario = request.user
            chamado.save()
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
