from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import ChamadoForm
from .models import Chamado

@login_required
def criar_chamado(request):
    if request.method == 'POST':
        form = ChamadoForm(request.POST)
        if form.is_valid():
            chamado = form.save(commit=False)
            chamado.usuario = request.user
            chamado.save()
            return redirect('lista_chamados')
        
    else:
            form = ChamadoForm()

    return render(request, 'chamados/criar.html', {'form': form})

@login_required
def lista_chamados(request):

     # REGRA DE NEGÓCIO:
    # Se o usuário for um Administrador/Técnico (is_staff no Django Admin)

    if request.user.is_staff:
        chamados = Chamado.objects.all()

    else:
         chamados = Chamado.objects.filter(usuario=request.user)

    return render(render, 'chamados/lista.html', {'chamados': chamados})
     