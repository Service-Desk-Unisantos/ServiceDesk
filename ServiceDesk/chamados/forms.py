from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import Chamado


class ChamadoForm(forms.ModelForm):
    class Meta:
        model = Chamado
        # Campos necessarios para o registro do chamado, incluindo categoria (RF03).
        fields = ["titulo", "descricao", "categoria", "prioridade"]
        widgets = {
            "titulo": forms.TextInput(
                attrs={"placeholder": "Ex.: Erro ao acessar o sistema interno"}
            ),
            "descricao": forms.Textarea(
                attrs={"placeholder": "Descreva o problema com o maximo de detalhes"}
            ),
            "categoria": forms.Select(),
            "prioridade": forms.Select(),
        }


class CadastroUsuarioForm(UserCreationForm):
    # Campo extra para o cadastro do usuario (RF01).
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "password1", "password2")
        labels = {
            "username": "Usuario",
            "first_name": "Nome",
            "last_name": "Sobrenome",
            "email": "E-mail",
            "password1": "Senha",
            "password2": "Confirmacao da senha",
        }


class LoginUsuarioForm(AuthenticationForm):
    username = forms.CharField(
        label="Usuario ou e-mail",
        widget=forms.TextInput(
            attrs={
                "autofocus": True,
                "placeholder": "Digite seu usuario ou e-mail",
            }
        ),
    )
