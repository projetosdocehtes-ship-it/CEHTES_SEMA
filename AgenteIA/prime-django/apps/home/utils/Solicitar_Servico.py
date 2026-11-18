from django.utils import timezone

from apps.cartorios.models import Usuario
from apps.home.models import Colaborador, Event, TipoFaseProtocoloColaborador
from apps.home.templatetags.home_formatos import (
    get_nome_colaborador_pelo_id,
    mapear_nome_colaborador,
)


def colaborador_solicitar_servico(colaborador_id):
    # Variável para contar a quantidade de colaboradores
    quantidade_colaboradores, nome_colaboradores, fase_id_procurar, descricao = (
        0,
        [],
        [0],
        "",
    )

    colaborador = Colaborador.objects.filter(pk=colaborador_id).first()

    # Filtrar os grupos que o colaborador faz o pedido de servico (fase anterior)
    grupo_solicitar = TipoFaseProtocoloColaborador.objects.filter(
        funcionarios=colaborador,
    ).values_list("fase_protocolos_solicitar_servicos_id", "descricao")

    # O grupo e o texto a enviar
    for fase_id, desc in grupo_solicitar:
        fase_id_procurar = [int(fase_id)]
        descricao = str(desc)

    colaboradores = list(
        TipoFaseProtocoloColaborador.objects.filter(
            fase_protocolos_id__in=fase_id_procurar,
        ).values_list("funcionarios", flat=True),
    )

    # Obter lista de colaboradores que estão vencendo
    colaboradores_com_protocolo_vencendo = Usuario.get_usuarios_com_protocolo_vencendo()

    # Extendendo a lista original com a nova lista, se não estiver vazia
    if colaboradores_com_protocolo_vencendo.exists():
        colaboradores.extend(colaboradores_com_protocolo_vencendo.id)

    # RETIRAR O FUNCIONARIO
    if colaborador in colaboradores:
        colaboradores.remove(colaborador)

    # Data para registrar a solicitacao
    data_evento = timezone.now()

    # Buscar todos os colaboradores necessários em uma única consulta
    colaboradores = Colaborador.objects.filter(pk__in=colaboradores).values(
        "colaborador",
        "nome",
    )

    # Criar um dicionário para mapear colaborador para nome
    {col["colaborador"]: col["nome"] for col in colaboradores}

    # Descricao de quem pediu o SERVICO
    descricao = (
        str(descricao)
        + ": "
        + mapear_nome_colaborador(get_nome_colaborador_pelo_id(colaborador_id))
    )

    # Processar cada colaborador
    for colaborador in colaboradores:
        try:
            nome_colaborador = mapear_nome_colaborador(
                get_nome_colaborador_pelo_id(colaborador.pk),
            )
            nome_colaboradores.append(nome_colaborador)

            # Montar o evento e gravar no BD
            Event.montar_evento(
                usuario_id=nome_colaborador,
                desc=descricao,
                url="",
                title=descricao,
                hour=data_evento.hour,
                minuto=data_evento.minute,
                year_inicio=data_evento.year,
                month_inicio=data_evento.month,
                day_inicio=data_evento.day,
                year_fim=data_evento.year,
                month_fim=data_evento.month,
                day_fim=data_evento.day,
                colaborador_id=colaborador.pk,
            )

            quantidade_colaboradores += 1
        except Exception as e:
            print("ERRO: ", e)

    print("Solicitou serviço:", colaborador)

    return quantidade_colaboradores, ", ".join(set(nome_colaboradores))
