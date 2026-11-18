import logging

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")


def ajustar_sequence(nome_da_tabela: str, nome_da_sequence: str) -> None:
    from django.db import connection

    """Ajusta a sequence de uma tabela para o próximo valor disponível após o maior ID."""
    logger.debug(
        f"Iniciando ajuste da sequence para a tabela '{nome_da_tabela}' e sequence '{nome_da_sequence}'.",
    )

    with connection.cursor() as cursor:
        try:
            # Consulta para obter o maior ID da tabela
            cursor.execute(f"SELECT MAX(id) FROM {nome_da_tabela}")
            max_id = cursor.fetchone()[0]

            if max_id is not None:
                # Ajusta a sequence para o próximo valor após o maior ID
                cursor.execute("SELECT setval(%s, %s)", [nome_da_sequence, max_id + 1])
                logger.info(
                    f"Sequence '{nome_da_sequence}' ajustada para {max_id + 1}.",
                )
            else:
                logger.warning(
                    f"Nenhum ID encontrado na tabela '{nome_da_tabela}'. Sequence '{nome_da_sequence}' não foi ajustada.",
                )
        except Exception as e:
            logger.exception(
                f"Erro ao ajustar a sequence '{nome_da_sequence}' para a tabela '{nome_da_tabela}': {e}",
            )
            raise

    logger.debug(f"Finalizado ajuste da sequence para a tabela '{nome_da_tabela}'.")

    return max_id + 1
