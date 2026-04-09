from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Chamado


class FluxoAutenticacaoTests(TestCase):
    def test_cadastro_cria_usuario_e_autentica(self):
        # RF01: novo usuario deve conseguir se cadastrar na plataforma.
        response = self.client.post(
            reverse("cadastro_usuario"),
            {
                "username": "ana",
                "first_name": "Ana",
                "last_name": "Silva",
                "email": "ana@example.com",
                "password1": "SenhaForte123!",
                "password2": "SenhaForte123!",
            },
        )

        self.assertRedirects(response, reverse("lista_chamados"))
        self.assertTrue(User.objects.filter(username="ana").exists())

    def test_login_autentica_usuario_existente(self):
        # RF02: usuario cadastrado deve conseguir fazer login.
        User.objects.create_user(username="bruno", password="SenhaForte123!")

        response = self.client.post(
            reverse("login_usuario"),
            {"username": "bruno", "password": "SenhaForte123!"},
        )

        self.assertRedirects(response, reverse("lista_chamados"))

    def test_rotas_protegidas_redirecionam_para_login(self):
        # Garantia de seguranca: sem login, o usuario nao acessa o painel/novo chamado.
        response_lista = self.client.get(reverse("lista_chamados"))
        response_novo = self.client.get(reverse("criar_chamado"))

        self.assertEqual(response_lista.status_code, 302)
        self.assertIn(reverse("login_usuario"), response_lista.url)
        self.assertEqual(response_novo.status_code, 302)
        self.assertIn(reverse("login_usuario"), response_novo.url)


class ChamadosTests(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user(username="cliente", password="SenhaForte123!")
        self.outro_usuario = User.objects.create_user(
            username="outro", password="SenhaForte123!"
        )
        self.staff = User.objects.create_user(
            username="tecnico", password="SenhaForte123!", is_staff=True
        )

    def test_usuario_comum_visualiza_apenas_proprios_chamados(self):
        # RF04: usuario comum visualiza apenas os chamados que ele criou.
        Chamado.objects.create(
            titulo="Chamado do cliente",
            descricao="Descricao A",
            categoria="software",
            prioridade="baixa",
            usuario=self.usuario,
        )
        Chamado.objects.create(
            titulo="Chamado de outro usuario",
            descricao="Descricao B",
            categoria="hardware",
            prioridade="media",
            usuario=self.outro_usuario,
        )

        self.client.login(username="cliente", password="SenhaForte123!")
        response = self.client.get(reverse("lista_chamados"))

        self.assertContains(response, "Chamado do cliente")
        self.assertNotContains(response, "Chamado de outro usuario")

    def test_staff_visualiza_todos_os_chamados(self):
        # RF04: perfil tecnico/admin pode acompanhar todos os chamados.
        Chamado.objects.create(
            titulo="Chamado A",
            descricao="Descricao A",
            categoria="rede",
            prioridade="alta",
            status="aberto",
            usuario=self.usuario,
        )
        Chamado.objects.create(
            titulo="Chamado B",
            descricao="Descricao B",
            categoria="acesso",
            prioridade="media",
            status="andamento",
            usuario=self.outro_usuario,
        )

        self.client.login(username="tecnico", password="SenhaForte123!")
        response = self.client.get(reverse("lista_chamados"))

        self.assertContains(response, "Chamado A")
        self.assertContains(response, "Chamado B")
        # RF05: status deve aparecer no painel para acompanhamento.
        self.assertContains(response, "Em andamento")

    def test_registro_de_chamado_salva_categoria(self):
        # RF03: registro inclui titulo, descricao e categoria.
        self.client.login(username="cliente", password="SenhaForte123!")
        response = self.client.post(
            reverse("criar_chamado"),
            {
                "titulo": "Sem acesso ao sistema",
                "descricao": "Nao consigo entrar com meu usuario.",
                "categoria": "acesso",
                "prioridade": "alta",
            },
        )

        self.assertRedirects(response, reverse("lista_chamados"))
        chamado = Chamado.objects.get(titulo="Sem acesso ao sistema")
        self.assertEqual(chamado.categoria, "acesso")
        self.assertEqual(chamado.status, "aberto")
        self.assertEqual(chamado.usuario, self.usuario)
