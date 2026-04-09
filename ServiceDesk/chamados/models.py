from django.contrib.auth.models import User
from django.db import models


class Chamado(models.Model):
    # Status para acompanhamento do atendimento (RF05).
    STATUS_CHOICES = [
        ("aberto", "Aberto"),
        ("andamento", "Em andamento"),
        ("fechado", "Fechado"),
    ]

    # Prioridade definida no momento da abertura do chamado.
    PRIORIDADE_CHOICES = [
        ("baixa", "Baixa"),
        ("media", "Media"),
        ("alta", "Alta"),
    ]

    # Categoria da solicitacao, exigida no requisito de registro (RF03).
    CATEGORIA_CHOICES = [
        ("hardware", "Hardware"),
        ("software", "Software"),
        ("rede", "Rede"),
        ("acesso", "Acesso"),
        ("outros", "Outros"),
    ]

    titulo = models.CharField(max_length=100)
    descricao = models.TextField()
    categoria = models.CharField(
        max_length=20, choices=CATEGORIA_CHOICES, default="outros"
    )
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="aberto")
    prioridade = models.CharField(max_length=20, choices=PRIORIDADE_CHOICES)
    data_criacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Exibe os chamados mais recentes primeiro no painel.
        ordering = ["-data_criacao"]

    def __str__(self):
        return self.titulo


class Comentario(models.Model):
    # Relacionamento entre comentarios e chamado.
    chamado = models.ForeignKey(
        Chamado, on_delete=models.CASCADE, related_name="comentarios"
    )
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    texto = models.TextField()
    data = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.usuario} - {self.chamado}"
