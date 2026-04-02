from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import ChamadoForm

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