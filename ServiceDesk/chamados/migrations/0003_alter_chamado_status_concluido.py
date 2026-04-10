from django.db import migrations, models


def converter_status_fechado_para_concluido(apps, schema_editor):
    # Migra registros legados para o novo valor de status padronizado.
    Chamado = apps.get_model("chamados", "Chamado")
    Chamado.objects.filter(status="fechado").update(status="concluido")


def reverter_status_concluido_para_fechado(apps, schema_editor):
    # Mantem reversibilidade da migration em caso de rollback.
    Chamado = apps.get_model("chamados", "Chamado")
    Chamado.objects.filter(status="concluido").update(status="fechado")


class Migration(migrations.Migration):
    dependencies = [
        ("chamados", "0002_alter_chamado_options_chamado_categoria"),
    ]

    operations = [
        migrations.AlterField(
            model_name="chamado",
            name="status",
            field=models.CharField(
                choices=[
                    ("aberto", "Aberto"),
                    ("andamento", "Em andamento"),
                    ("concluido", "Concluido"),
                ],
                default="aberto",
                max_length=20,
            ),
        ),
        migrations.RunPython(
            converter_status_fechado_para_concluido,
            reverter_status_concluido_para_fechado,
        ),
    ]
