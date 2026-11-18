import logging

from django.apps import apps
from django.db import connection, transaction
from django.db.models.signals import post_migrate
from django.db.utils import IntegrityError, ProgrammingError
from django.dispatch import Signal, receiver

SIGNALS_IMPORTED = True


logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")


@receiver(post_migrate)
def post_migrate_populate_initial_data_logradouro(sender, **kwargs) -> None:
    if sender.name == "apps.home":
        from apps.home.models import TipoLogradouro

        logger.info("Populando dados iniciais para TipoLogradouro em Home")
        try:
            TipoLogradouro.objects.criar_padroes()
        except Exception as e:
            logger.exception(f"Erro ao popular dados iniciais para TipoLogradouro {e}")


@receiver(post_migrate)
def post_migrate_populate_initial_data_status_protocolo(sender, **kwargs) -> None:
    if sender.name == "apps.home":
        try:
            from apps.home.models import StatusProtocolo

            # obtem o model StatusProtocolo
            status_protocolo = apps.get_model("home", "StatusProtocolo")

            # Verifica se há algum registro de StatusProtocolo no banco
            if not status_protocolo.objects.exists():
                logger.info("Populando dados para StatusProtocolo")
                # Se não houverem registros, criar registros iniciais
                status_descricoes = [
                    StatusProtocolo.EM_ANDAMENTO,
                    StatusProtocolo.EXIGENCIA,
                    StatusProtocolo.CANCELADO,
                    StatusProtocolo.REGISTRADO,
                    StatusProtocolo.SUBJUDICE,
                    StatusProtocolo.EM_REGISTRO,
                    StatusProtocolo.PRONTO_PARA_REGISTRAR,
                    StatusProtocolo.DISTRIBUIDO,
                ]
                for descricao in status_descricoes:
                    status_protocolo.objects.create(descricao=descricao)
        except Exception:
            logger.exception("Erro ao criar dados iniciais para StatusProtocolo")


@receiver(post_migrate)
def populate_initial_data_tipo_fase_protocolo(sender, **kwargs) -> None:
    if sender.name != "apps.home":
        return

    try:
        # obtem o model StatusProtocolo
        from apps.home.models import TipoFaseProtocolo

        logger.info("Populando dados para TipoFaseProtocolo")

        # Verifica se há algum registro de TipoFaseProtocolo no banco
        if not TipoFaseProtocolo.objects.exists():
            TipoFaseProtocolo.objects.criar_defaults()

    except Exception:
        logger.exception("Erro ao criar dados iniciais para TipoFaseProtocolo")


@receiver(post_migrate)
def popular_tipo_integracao(sender, **kwargs) -> None:
    if sender.name != "apps.home":
        return

    try:
        # obtem o model StatusProtocolo
        from apps.comum.models import TipoIntegracao

        logger.info("Populando dados para TipoIntegracao")

        # Verifica se há algum registro de TipoFaseProtocolo no banco
        TipoIntegracao.criar_tipo_integracao_padrao()

    except Exception:
        logger.exception("Erro ao criar dados iniciais para TipoFaseProtocolo")


@receiver(post_migrate)
def populate_initial_data_modelo_de_texto_exemplo(sender, **kwargs) -> None:
    if sender.name == "apps.home":
        try:
            # obtem o model StatusProtocolo
            modelo_texto_model = apps.get_model("home", "ModeloTexto")
            tipo_modelo_texto_model = apps.get_model("home", "TipoModelo")

            # Verifica se há algum registro de TipoFaseProtocolo no banco
            if not modelo_texto_model.objects.exists():
                logger.info("Criando modelo de texto de exemplo")
                # Se não houver registros, criar registros iniciais
                modelo_texto_model.objects.create(
                    titulo="Modelo de Exemplo Modelos para Andamentos",
                    conteudo="Este é um modelo de texto de exemplo para Andamentos",
                    tipo=tipo_modelo_texto_model.objects.get_or_create(
                        descricao="Modelos para Andamentos",
                    )[0],
                )
                tipo_modelo_texto_certidao = (
                    tipo_modelo_texto_model.objects.get_or_create(
                        descricao="Modelos para Certdiões",
                    )[0],
                )
                modelo_texto_model.objects.create(
                    titulo="Modelo para Certidão Negativa de Ônus",
                    conteudo="""CERTIDÃO NEGATIVA DE ÔNUS

                        Eu, Serventuário do Cartório do Projeto CEHTES, desta cidade e comarca de Alfenas, Estado de Minas Gerais, na forma da lei, etc.

                        Certifico e dou fé, a requerimento verbal de pessoa interessada, que revendo neste cartório, os Livros de Registro Geral e de Registro Auxiliar, neles, com relação ao imóvel de propriedade de: , , , , : , residente , constante de: , não encontrei nenhum ônus, tais como: hipotecas, cláusulas de inalienabilidade, impenhorabilidade, rendas temporárias, uso, usufruto, habitação, servidão, fideicomisso, arrestos, sequestro, protesto contra alienação de bens, e outros que possam afetar a posse ou domínio dos proprietários atuais ou de seus antecessores.

                        É o que tenho a certificar, pelo que dou fé.



                        Alfenas, 29 de julho de 2024

                        A presente certidão foi emitida e assinada digitalmente nos termos da MP 2.200/01 e Lei nº 11.977/09, somente sendo válida em meio digital, sendo o acesso realizado através do site https://registradores.onr.org.br/.


                        Assinada eletronicamente por: Cristofer Augusto de Freitas Costa Biscaro.

                        Emol: R$26,11; ISSQN: R$0,52; Tfj: R$9,78; Recompe R$1,57; Total: R$37,98

                        PROTOCOLO ONR: S24070750651D

                        """,
                    tipo=tipo_modelo_texto_certidao,
                )

        except Exception as e:
            logger.exception(f"Erro ao criar dados iniciais para ModeloTexto: {e}")


@receiver(post_migrate)
def corrige_nomes_dos_colaboradores(sender, **kwargs) -> None:
    if sender.name == "apps.home":
        try:
            # Usuario = apps.get_model("cartorios", "Usuario")
            # colabroador = apps.get_model("home", "Colaborador")

            # for usuario in Usuario.objects.all():
            #     nome_mapeado = formatar_nome(
            #         Usuario.NOME_MAP.get(
            #             str(usuario.username).upper(),
            #             usuario.username,
            #         ),
            #     )
            #     # Verifica se o nome precisa ser atualizado para evitar salvar desnecessariamente
            #     if usuario.username.upper() != nome_mapeado.upper():
            #         usuario.username = nome_mapeado
            #         usuario.nome_completo = nome_mapeado
            #         usuario.first_name = nome_mapeado.split(" ")[0]
            #         usuario.last_name = " ".join(nome_mapeado.split(" ")[1:])
            #         try:
            #             usuario.save()
            #             logger.info(f"Atualizado: {usuario.username}")
            #         except Exception:
            #             pass

            # for _colaborador in colabroador.objects.all():
            #     nome_mapeado = formatar_nome(
            #         Usuario.NOME_MAP.get(usuario.username, usuario.username),
            #     )
            #     # Verifica se o nome precisa ser atualizado para evitar salvar desnecessariamente
            #     if usuario.username.upper() != nome_mapeado.upper():
            #         usuario.username = nome_mapeado
            #         usuario.nome_completo = nome_mapeado
            #         usuario.first_name = nome_mapeado.split(" ")[0]
            #         usuario.last_name = " ".join(nome_mapeado.split(" ")[1:])
            #         try:
            #             usuario.save()
            #             logger.info(f"Atualizado: {usuario.username}")
            #         except Exception:
            #             pass

            logger.info("Corrigindo nomes dos Colabroadores com base no MAPA")

        except Exception as e:
            logger.exception(f"Erro ao corrigir nomes dos colaboradores: {e}")


documento_assinado_signal = Signal()


@receiver(post_migrate)
def populate_initial_data_motivo_assinatura(sender, **kwargs) -> None:
    if sender.name == "apps.home":
        try:
            # obtem o model StatusProtocolo
            model = apps.get_model("home", "MotivoAssinaturaDigital")

            # Verifica se há algum registro de TipoFaseProtocolo no banco
            if not model.objects.exists():
                logger.info("Populando dados para MotivoAssinaturaDigital")
                # Se não houver registros, criar registros iniciais
                model.objects.create(descricao="Entrega de Exigência")
        except Exception as e:
            logger.exception(
                f"Erro ao criar dados iniciais para MotivoAssinaturaDigital: {e}",
            )


@receiver(post_migrate)
def populate_initial_data_tipo_documento(sender, **kwargs) -> None:
    if sender.name == "apps.home":
        try:
            # obtem o model StatusProtocolo
            model = apps.get_model("home", "TipoDocumentoAssinatura")

            # Verifica se há algum registro de TipoFaseProtocolo no banco
            if not model.objects.exists():
                logger.info(
                    "Populando dados para Tipo de Documento de Assinatura",
                )
                # Se não houver registros, criar registros iniciais
                model.objects.create(descricao="Exigência")
                model.objects.create(descricao="Certidão")
                model.objects.create(descricao="Requerimento")
        except Exception as e:
            logger.exception(
                f"Erro ao criar dados iniciais para TipoDocumentoAssinatura {e}",
            )


@receiver(post_migrate)
def rename_sequences_based_on_pks(sender, **kwargs):
    if sender.name == "apps.home":
        with connection.cursor() as cursor:
            try:
                # Encontrar todas as PKs e suas sequences no banco de dados
                cursor.execute(
                    """
                SELECT
                    t.relname AS table_name,
                    a.attname AS column_name,
                    c.relname AS sequence_name
                FROM
                    pg_class t
                JOIN
                    pg_attribute a ON a.attrelid = t.oid
                JOIN
                    pg_depend d ON d.refobjid = t.oid AND d.refobjsubid = a.attnum
                JOIN
                    pg_class c ON c.oid = d.objid AND c.relkind = 'S'
                JOIN
                    pg_index i ON i.indrelid = t.oid
                WHERE
                    a.attnum > 0 AND a.attisdropped = false AND i.indisprimary = true
                """,
                )
                sequences_info = cursor.fetchall()

                # Processa cada tabela e sequence encontrada
                logger.info("Renomeando sequences baseadas nas PKs correspondentes")
                for table_name, column_name, sequence_name in sequences_info:
                    # logger.info(f"Verificando sequence {sequence_name} baseada na PK da tabela {table_name}")
                    new_sequence_name = f"{table_name}_{column_name}_seq"
                    if sequence_name != new_sequence_name:
                        logger.info(
                            f"    Renomeando sequence {sequence_name} para {new_sequence_name}",
                        )
                        cursor.execute(
                            f"""
                        DO $$
                        BEGIN
                            IF EXISTS (SELECT FROM pg_class WHERE relkind = 'S' AND relname = '{sequence_name}') THEN
                                EXECUTE 'ALTER SEQUENCE {sequence_name} RENAME TO {new_sequence_name}';
                            ELSE
                                RAISE NOTICE 'A sequence {sequence_name} não existe.';
                            END IF;
                        END $$;
                        """,
                        )
            except Exception as e:
                logger.exception(f"Erro ao renomear sequences baseadas nas PKs {e}")


@receiver(post_migrate)
def adjust_sequences_to_max_pk(sender, **kwargs):
    if sender.name == "apps.home":
        with connection.cursor() as cursor:
            try:
                # Consulta para encontrar todas as sequences e os campos de chave primária correspondentes
                cursor.execute(
                    """
                SELECT
                    t.relname AS table_name,
                    a.attname AS column_name,
                    c.relname AS sequence_name
                FROM
                    pg_class t
                JOIN
                    pg_attribute a ON a.attrelid = t.oid
                JOIN
                    pg_depend d ON d.refobjid = t.oid AND d.refobjsubid = a.attnum
                JOIN
                    pg_class c ON c.oid = d.objid AND c.relkind = 'S'
                JOIN
                    pg_index i ON i.indrelid = t.oid
                WHERE
                    a.attnum > 0 AND a.attisdropped = false AND i.indisprimary = true
                """,
                )
                sequences_info = cursor.fetchall()

                # Para cada sequence encontrada, verificar e ajustar o valor se necessário
                logger.info(
                    "Conferindo valor maximo das sequences com base no valor máximo da PK correspondente",
                )
                for table_name, column_name, sequence_name in sequences_info:
                    cursor.execute(f"SELECT MAX({column_name}) FROM {table_name}")
                    max_id = cursor.fetchone()[0] or 0  # Usa 0 se não houver registros
                    new_val = max_id

                    # Verifica o valor atual da sequence
                    cursor.execute(f"SELECT last_value FROM {sequence_name}")
                    current_val = cursor.fetchone()[0]

                    if current_val < new_val and new_val > 0:
                        logger.info(
                            f"    Ajustando sequence {sequence_name} de {current_val} para {new_val}",
                        )
                        cursor.execute(
                            f"SELECT setval('{sequence_name}', {new_val}, false);",
                        )

            except Exception as e:
                logger.exception(
                    f"Erro ao ajustar sequences para o valor máximo da PK: {e}",
                )


@receiver(post_migrate)
def populate_initial_data_of_finalidade(sender, **kwargs) -> None:
    if sender.name == "apps.home":
        try:
            from apps.home.models import Finalidade

            Finalidade.objects.criar_defaults()
        except Exception as e:
            logger.exception(f"Erro ao criar ou atualizar finalidades de certidão: {e}")


@receiver(post_migrate)
def populate_initicial_data_tipo_apresentate(sender, **kwargs) -> None:
    if sender.name == "apps.home":
        try:
            from apps.home.models import TipoApresentante

            TipoApresentante.criar_defaults()
        except Exception as e:
            logger.exception(f"Erro ao criar ou atualizar tipos de apresentantes: {e}")


@receiver(post_migrate)
def popular_dados_iniciais_tipo_categoria_financeira(sender, **kwargs) -> None:
    if sender.name == "apps.home":
        try:
            from apps.home.models import TipoCategoriaFinanceira

            TipoCategoriaFinanceira.criar_padroes()
        except Exception as e:
            logger.exception(
                f"Erro ao criar ou atualizar os TIPOS DE CATEGORIAS FINANCEIRAS: {e}",
            )


@receiver(post_migrate)
def popular_dados_iniciais_tipo_operacao_financeira(sender, **kwargs) -> None:
    if sender.name == "apps.home":
        try:
            from apps.home.models import TipoOperacaoFinanceira

            TipoOperacaoFinanceira.criar_padroes()
        except Exception as e:
            logger.exception(
                f"Erro ao criar ou atualizar os TIPOS DE OPERACOES FINANCEIRAS: {e}",
            )


@receiver(post_migrate)
def popular_dados_iniciais_tipo_transacao_financeira(sender, **kwargs) -> None:
    if sender.name == "apps.home":
        try:
            from apps.home.models import TipoTransacaoFinanceira

            TipoTransacaoFinanceira.criar_padroes()
        except Exception as e:
            logger.exception(
                f"Erro ao criar ou atualizar os TIPOS DE TRANSACOES FINANCEIRAS: {e}",
            )


@receiver(post_migrate)
def popular_dados_iniciais_de_prazo_legal(sender, **kwargs) -> None:
    if sender.name == "apps.home":
        try:
            from apps.home.models import PrazoLegal

            PrazoLegal.criar_padroes()
        except Exception as e:
            logger.exception(f"Erro ao criar ou atualizar os PRAZOS LEGAIS: {e}")


@receiver(post_migrate)
def popular_dados_tipos_certidao_onr(sender, **kwargs) -> None:
    if sender.name == "apps.home":
        try:
            pass

            #TipoCertidao.popular_valores_onr()

        except Exception as e:
            logger.exception(f"Erro ao popular dados com Tipo De Certidões da ONR: {e}")


@receiver(post_migrate)
def popular_dados_tipo_classe_registro(sender, **kwargs) -> None:
    if sender.name == "apps.home":
        try:
            logger.info("Populando Tipo de Classe do Registro")
            from apps.home.models import TipoClasseRegistro

            TipoClasseRegistro.criar_padroes()
        except Exception as e:
            logger.exception(f"Erro ao popular Tipo de Classe do Registro: {e}")


@receiver(post_migrate)
def create_tipos_documento(sender, **kwargs) -> None:
    if sender.name == "apps.comum":
        TipoDocumento = apps.get_model("comum", "TipoDocumento")

        try:
            # logger.info("Verificados dados de TipoDocumento no banco de dados:")
            if not TipoDocumento.objects.exists():
                TipoDocumento.objects.create(
                    sigla="CPF",
                    nome="Cadastro Nacional de Pessoa Física",
                )
                TipoDocumento.objects.create(
                    sigla="CNPJ",
                    nome="Cadastro Nacional de Pessoa Jurídica",
                )
            logger.info("Tipos de Documento criados/atualizados!")
        except ProgrammingError as e:
            logger.exception(
                f"ERRO ao acessar a tabela TipoDocumento no banco de dados: {e}",
            )


@receiver(post_migrate)
def create_tipo_tributacao(sender, **kwargs) -> None:
    if sender.name == "apps.comum":
        TipoTributacao = apps.get_model("comum", "TipoTributacao")

        try:
            # logger.info("Verificados dados de TipoTributacao no banco de dados:")
            if not TipoTributacao.objects.exists():
                TipoTributacao.objects.create(
                    nome="Normal",
                    descricao="Normal",
                    percentual_desconto=0,
                )
                TipoTributacao.objects.create(
                    nome="MCMV 50%",
                    descricao="Programa Minha Casa Minha Vida",
                    percentual_desconto=50,
                )
                TipoTributacao.objects.create(
                    nome="SFH 50%",
                    descricao="Sistema Financeiro de Habitação",
                    percentual_desconto=50,
                )
                TipoTributacao.objects.create(
                    nome="Tabela Cartorária 80%",
                    descricao="Tabela Cartóraria",
                    percentual_desconto=80,
                )
                TipoTributacao.objects.create(
                    nome="Isento 100%",
                    descricao="Isento",
                    percentual_desconto=100,
                )
            logger.info(
                "Tipos de Tributação criados/atualizados!",
            )
        except ProgrammingError as e:
            logger.exception(
                f"ERRO ao acessar a tabela TipoTributacao no banco de dados: {e}",
            )


@receiver(post_migrate)
def create_tipos_papel_parte(sender, **kwargs) -> None:
    if sender.name == "apps.comum":
        TipoPapelParte = apps.get_model("comum", "TipoPapelParte")

        try:
            if not TipoPapelParte.objects.exists():
                papeis = [
                    {
                        "nome": "Adquirente",
                        "descricao": "A pessoa ou entidade que está adquirindo a propriedade. Responsável pelo pagamento e assumindo a posse do imóvel.",
                    },
                    {
                        "nome": "Transmitente",
                        "descricao": "O proprietário atual que está vendendo ou transferindo a propriedade. Responsável pela entrega do imóvel ao adquirente.",
                    },
                    {
                        "nome": "Devedor Hipotecário",
                        "descricao": "A pessoa que está recebendo o financiamento para a compra do imóvel, utilizando-o como garantia no acordo.",
                    },
                    {
                        "nome": "Credor Hipotecário",
                        "descricao": "A instituição financeira ou credor que fornece o empréstimo para a compra do imóvel, detendo a hipoteca como segurança.",
                    },
                    {
                        "nome": "Fiador",
                        "descricao": "Pessoa ou entidade que garante o cumprimento das obrigações financeiras do devedor, assumindo a responsabilidade em caso de inadimplência.",
                    },
                    {
                        "nome": "Testemunha",
                        "descricao": "Indivíduos que presenciam a assinatura do documento, atestando a identidade das partes e a integridade do processo.",
                    },
                    {
                        "nome": "Interveniente Anuente",
                        "descricao": "Parte que, embora não seja principal na transação, tem interesse legal no ato e consente com a realização do mesmo.",
                    },
                    {
                        "nome": "Herdeiro",
                        "descricao": "Pessoa que legalmente recebe parte ou todo o imóvel em caso de falecimento do proprietário.",
                    },
                    {
                        "nome": "Procurador",
                        "descricao": "Representante legal que atua em nome de outra pessoa no ato, sob uma autorização formal conhecida como procuração.",
                    },
                    {
                        "nome": "Oficial de Registro",
                        "descricao": "Profissional responsável por registrar formalmente o ato no cartório de imóveis, garantindo a legalidade e autenticidade do registro.",
                    },
                    {
                        "nome": "Avaliador",
                        "descricao": "Profissional qualificado para determinar o valor de mercado do imóvel.",
                    },
                ]

                for papel in papeis:
                    TipoPapelParte.objects.get_or_create(
                        nome=papel["nome"],
                        defaults={"descricao": papel["descricao"]},
                    )

            logger.info(
                "Tipos de Papéis de Partes criados/atualizados!",
            )
        except ProgrammingError as e:
            logger.exception(
                f"ERRO ao acessar a tabela TipoPapelParte no banco de dados: {e}",
            )


@receiver(post_migrate)
def popular_unidades_federativas_padroes(sender, **kwargs) -> None:
    if sender.name == "apps.comum":
        try:
            from apps.comum.models import UnidadeFederativa

            UnidadeFederativa.criar_unidades_federativas_padroes()
            logger.info("Unidades Federativas criadas e atualizadas.")
        except Exception as e:
            logger.exception(f"Erro ao criar Unidades Federativas Padrões: {e}")


@receiver(post_migrate)
def popular_municipios(sender, **kwargs) -> None:
    if sender.name == "apps.comum":
        try:
            from apps.comum.models import Municipio

            Municipio.criar_municipios_default()
        except Exception as e:
            logger.exception(f"Erro ao criar municipios padrões: {e}")


@receiver(post_migrate)
def create_tipos_de_logradouro(sender, **kwargs) -> None:
    if sender.name == "apps.comum":
        try:
            from apps.comum.models import TipoLogradouro

            TipoLogradouro.create_tipos_de_logradouro()
        except Exception as e:
            logger.exception(f"Erro ao criar Tipos de Lograoudo padrões: {e}")


@receiver(post_migrate)
def create_tipos_de_certidoes(sender, **kwargs) -> None:
    if sender.name == "apps.comum":
        TipoCertidaoComum = apps.get_model("comum", "TipoCertidaoComum")
        PrazoLegal = apps.get_model("comum", "PrazoLegal")
        TipoCartorio = apps.get_model("comum", "TipoCartorio")

        prazo_legal = PrazoLegal.get_default_prazo_legal()
        tipo_registro_de_imoveis_id = TipoCartorio.get_cartorio_registro_imoveis_id()

        certidoes = [
            "Certidão de Inteiro Teor",
            "Certidão de Matrícula",
            "Certidão de Ônus",
            "Certidão de Propriedade",
            "Certidão de Registro",
            "Certidão de Ações",
            "Certidão de Ônus Reais",
            "Certidão de Penhora",
        ]

        with transaction.atomic():
            try:
                for nome in certidoes:
                    TipoCertidaoComum.objects.get_or_create(
                        nome=nome,
                        defaults={
                            "prazo_legal": prazo_legal,
                            "tipo_cartorio_id": tipo_registro_de_imoveis_id,
                        },
                    )
                logger.info("Tipos de Certidão criados!")
            except IntegrityError as e:
                logger.exception(
                    f"Erro ao acessar ou criar tipos de certidão no banco de dados: {e!s}",
                )


@receiver(post_migrate)
def popular_dados_tipo_andamento_certidao(sender, **kwargs) -> None:
    if sender.name == "apps.home":
        try:
            logger.info("Populando dados para TipoAndamentoCertidao")

            #TipoAndamentoCertidao.criar_padroes()
        except Exception as e:
            logger.exception(
                f"Erro ao criar ou atualizar tipos de andamento de certidão: {e}",
            )


@receiver(post_migrate)
def reset_admin_password_signal(sender, **kwargs) -> None:
    if sender.name == "apps.home":
        try:
            pass

            #User.reset_or_create_admin_password()
        except Exception as e:
            logger.exception(f"Erro ao resetar a senha do usuário admin: {e}")


@receiver(post_migrate)
def criar_usuario_sistema(sender, **kwargs) -> None:
    if sender.name == "apps.home":
        try:
            pass

            #User.criar_usuario_sistema()
        except Exception as e:
            logger.exception(f"Erro ao criar usuário do sistema: {e}")
