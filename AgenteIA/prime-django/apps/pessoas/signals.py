from django.apps import apps
from django.db.models.signals import post_migrate
from django.db.utils import ProgrammingError
from django.dispatch import receiver

SIGNALS_IMPORTED = True


@receiver(post_migrate)
def populate_initial_data(sender, **kwargs) -> None:
    try:
        TipoVinculo = apps.get_model("pessoas", "TipoVinculo")
        # Verifica se há algum registro no banco de dados
        if not TipoVinculo.objects.exists():
            # Se não houver registros, executa a lógica, para criar registros iniciais
            TipoVinculo.objects.create(nome="Apresentante", papel="S")
            TipoVinculo.objects.create(nome="Adquirente", papel="A")
            TipoVinculo.objects.create(nome="Transmitente", papel="T")
            TipoVinculo.objects.create(nome="Credor", papel="C")
            TipoVinculo.objects.create(nome="Devedor", papel="D")
            TipoVinculo.objects.create(nome="Fiador", papel="F")
            TipoVinculo.objects.create(nome="Testemunha", papel="E")
            TipoVinculo.objects.create(nome="Procurador", papel="P")
            TipoVinculo.objects.create(nome="Requerente", papel="R")
            TipoVinculo.objects.create(nome="Avaliador", papel="V")
            TipoVinculo.objects.create(nome="Garantidor", papel="G")
            TipoVinculo.objects.create(nome="Interveniente", papel="I")
            TipoVinculo.objects.create(nome="Fiel Depositário", papel="L")
            TipoVinculo.objects.create(nome="Emitente", papel="M")
            TipoVinculo.objects.create(nome="Anuente", papel="N")
            TipoVinculo.objects.create(nome="Emitente e Fiel Depositário", papel="O")

    except ProgrammingError:
        print("ERRO ao acessar a tabela TipoVinculo no banco de dados: ")
