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

    def __init__(self, *args, **kwargs):
        # Aplica classe padrao para garantir alinhamento correto dos campos no frontend.
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            classes_atuais = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{classes_atuais} form-control".strip()


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
    # Campo de senha explicito para manter placeholder e compatibilidade com botao de olho.
    password = forms.CharField(
        label="Senha",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "current-password",
                "placeholder": "Digite sua senha",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        # Aplica classe padrao para o layout dos campos de login e do toggle de senha.
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            classes_atuais = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{classes_atuais} form-control".strip()
