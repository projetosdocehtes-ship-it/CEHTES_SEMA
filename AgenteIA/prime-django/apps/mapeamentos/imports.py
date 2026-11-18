from django.contrib.contenttypes.models import ContentType

from apps.mapeamentos.models import Mapeamento


def importar_atos_para_ato_praticavel() -> None:
    from apps.home.models import AtoPratica
    from apps.pedidos.models import AtoPraticavel

    # Busca todos os objetos Ato com chave primária positiva
    atos = AtoPratica.objects.filter(
        id__gt=0,
    )  # Filtra apenas os registros com ID maior que 0

    for ato in atos:
        # Verificar se já existe um mapeamento para o Ato
        content_type_antigo = ContentType.objects.get_for_model(ato)
        mapeamentos_existentes = Mapeamento.objects.filter(
            content_type_antigo=content_type_antigo,
            object_id_antigo=ato.pk,
        )

        if mapeamentos_existentes.exists():
            # Se já existe um mapeamento, pula para o próximo Ato
            continue

        # Verifica se já existe um AtoPraticavel com o mesmo nome
        nome_ato_praticavel = str(ato.tipo_ato).title()
        ato_praticavel_existente = AtoPraticavel.objects.filter(
            nome=nome_ato_praticavel,
        ).first()

        if ato_praticavel_existente:
            # Se já existe, reutiliza o AtoPraticavel existente
            ato_praticavel = ato_praticavel_existente
        else:
            # Se não existe, cria um novo AtoPraticavel
            ato_praticavel = AtoPraticavel(nome=nome_ato_praticavel)
            ato_praticavel.save()

        # Cria o mapeamento para o Ato, utilizando o AtoPraticavel existente ou o recém-criado
        content_type_novo = ContentType.objects.get_for_model(ato_praticavel)

        Mapeamento.objects.create(
            content_type_antigo=content_type_antigo,
            object_id_antigo=ato.pk,
            content_type_novo=content_type_novo,
            object_id_novo=ato_praticavel.pk,
        )


def importar_emolumentos_para_tipo_emolumentos() -> None:
    from apps.home.models import Emolumentos as ModelOrigem
    from apps.pedidos.models import TipoEmolumento as ModelDestino

    # Busca todos os objetos Ato com chave primária positiva
    objetos = ModelOrigem.objects.filter(_gt_id=0)

    for objeto_origem in objetos:
        # Verificar se já existe um mapeamento para o Ato
        content_type_antigo = ContentType.objects.get_for_model(objeto_origem)
        mapeamentos_existentes = Mapeamento.objects.filter(
            content_type_antigo=content_type_antigo,
            object_id_antigo=objeto_origem.pk,
        )

        if mapeamentos_existentes.exists():
            # Se já existe um mapeamento, pula para o próximo Ato
            continue

        # Verifica se já existe um objeto com o mesmo nome
        nome_objeto = str(objeto_origem.nome).title()
        objeto_existente = ModelDestino.objects.filter(nome=nome_objeto).first()

        if objeto_existente:
            # Se já existe, reutiliza o objeto existente
            objeto_destino = objeto_existente
        else:
            # Se não existe, cria um novo Objeto no destino.
            objeto_destino = ModelDestino(nome=nome_objeto)
            objeto_destino.save()

        # Cria o mapeamento para o objeto_destino, utilizando o objeto existente ou o recém-criado
        content_type_novo = ContentType.objects.get_for_model(objeto_destino)

        Mapeamento.objects.create(
            content_type_antigo=content_type_antigo,
            object_id_antigo=objeto_origem.pk,
            content_type_novo=content_type_novo,
            object_id_novo=objeto_destino.pk,
        )


def importar_titulos_protocolo_para_tipotitulo() -> None:
    from apps.home.models import Titulo as ModelOrigem
    from apps.pedidos.models import TipoTitulo as ModelDestino

    # Busca todos os objetos com chave primária positiva
    objetos = ModelOrigem.objects.filter(_gt_id=0)

    for objeto_origem in objetos:
        # Verificar se já existe um mapeamento para o Objeto
        content_type_antigo = ContentType.objects.get_for_model(objeto_origem)
        mapeamentos_existentes = Mapeamento.objects.filter(
            content_type_antigo=content_type_antigo,
            object_id_antigo=objeto_origem.pk,
        )

        if mapeamentos_existentes.exists():
            # Se já existe um mapeamento, pula para o próximo Objeto
            continue

        # Verifica se já existe um objeto com o mesmo nome
        nome_objeto = str(objeto_origem.tipo_titulo).title()
        objeto_existente = ModelDestino.objects.filter(nome=nome_objeto).first()

        if objeto_existente:
            # Se já existe, reutiliza o objeto existente
            objeto_destino = objeto_existente
        else:
            # Se não existe, cria um novo Objeto no destino.
            objeto_destino = ModelDestino(nome=nome_objeto)
            objeto_destino.save()

        # Cria o mapeamento para o objeto_destino, utilizando o objeto existente ou o recém-criado
        content_type_novo = ContentType.objects.get_for_model(objeto_destino)

        Mapeamento.objects.create(
            content_type_antigo=content_type_antigo,
            object_id_antigo=objeto_origem.pk,
            content_type_novo=content_type_novo,
            object_id_novo=objeto_destino.pk,
        )


def importar_tipos_de_estado_civil() -> None:
    from apps.home.models import EstadoCivil as ModelOrigem
    from apps.pedidos.models import TipoTitulo as ModelDestino

    # Busca todos os objetos com chave primária positiva
    objetos = ModelOrigem.objects.filter(_gt_id=0)

    for objeto_origem in objetos:
        # Verificar se já existe um mapeamento para o Objeto
        content_type_antigo = ContentType.objects.get_for_model(objeto_origem)
        mapeamentos_existentes = Mapeamento.objects.filter(
            content_type_antigo=content_type_antigo,
            object_id_antigo=objeto_origem.pk,
        )

        if mapeamentos_existentes.exists():
            # Se já existe um mapeamento, pula para o próximo Objeto
            continue

        # Verifica se já existe um objeto com o mesmo nome
        nome_objeto = str(objeto_origem.tipo_titulo).title()
        objeto_existente = ModelDestino.objects.filter(nome=nome_objeto).first()

        if objeto_existente:
            # Se já existe, reutiliza o objeto existente
            objeto_destino = objeto_existente
        else:
            # Se não existe, cria um novo Objeto no destino.
            objeto_destino = ModelDestino(nome=nome_objeto)
            objeto_destino.save()

        # Cria o mapeamento para o objeto_destino, utilizando o objeto existente ou o recém-criado
        content_type_novo = ContentType.objects.get_for_model(objeto_destino)

        Mapeamento.objects.create(
            content_type_antigo=content_type_antigo,
            object_id_antigo=objeto_origem.pk,
            content_type_novo=content_type_novo,
            object_id_novo=objeto_destino.pk,
        )


def importar_emolumentos_para_emolumentos() -> None:
    from apps.home.models import Emolumentos as ModelOrigem
    from apps.pedidos.models import Emolumento as ModelDestino

    # Busca todos os objetos Ato com chave primária positiva
    objetos = ModelOrigem.objects.filter(_gt_id=0)

    for objeto_origem in objetos:
        # Verificar se já existe um mapeamento para o Ato
        content_type_antigo = ContentType.objects.get_for_model(objeto_origem)
        mapeamentos_existentes = Mapeamento.objects.filter(
            content_type_antigo=content_type_antigo,
            object_id_antigo=objeto_origem.pk,
        )

        if mapeamentos_existentes.exists():
            # Se já existe um mapeamento, pula para o próximo Ato
            continue

        # Verifica se já existe um AtoPraticavel com o mesmo nome
        nome_ato_praticavel = str(objeto_origem.nome).title()
        ato_praticavel_existente = ModelDestino.objects.filter(
            nome=nome_ato_praticavel,
        ).first()

        if ato_praticavel_existente:
            # Se já existe, reutiliza o AtoPraticavel existente
            ato_praticavel = ato_praticavel_existente
        else:
            # Se não existe, cria um novo AtoPraticavel
            ato_praticavel = ModelDestino(nome=nome_ato_praticavel)
            ato_praticavel.save()

        # Cria o mapeamento para o Ato, utilizando o AtoPraticavel existente ou o recém-criado
        content_type_novo = ContentType.objects.get_for_model(ato_praticavel)

        Mapeamento.objects.create(
            content_type_antigo=content_type_antigo,
            object_id_antigo=objeto_origem.pk,
            content_type_novo=content_type_novo,
            object_id_novo=ato_praticavel.pk,
        )
