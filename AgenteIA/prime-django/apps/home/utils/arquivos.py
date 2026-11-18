# Configurar logging
import logging
import os

logger = logging.getLogger(__name__)


class GerenciadorDeArquivos:
    """
    Classe responsável por gerenciar uma lista de arquivos que precisam ser excluídos.

    Atributos:
        _arquivos_para_excluir (list): Lista interna de arquivos marcados para exclusão.
    """

    def __init__(self) -> None:
        """Inicializa a lista interna de arquivos para exclusão."""
        self._arquivos_para_excluir = []

    def adicionar_arquivo(self, arquivo) -> None:
        """
        Adiciona um arquivo à lista interna de arquivos marcados para exclusão.

        Args:
        ----
            arquivo (str): Caminho do arquivo a ser adicionado à lista.

        """
        self._arquivos_para_excluir.append(arquivo)

    def remover_arquivo(self, arquivo) -> None:
        """
        Remove um arquivo da lista interna de arquivos marcados para exclusão.

        Args:
        ----
            arquivo (str): Caminho do arquivo a ser removido da lista.

        Raises:
        ------
            ValueError: Se o arquivo não estiver presente na lista.

        """
        self._arquivos_para_excluir.remove(arquivo)

    def excluir_arquivos(self) -> None:
        """
        Exclui todos os arquivos presentes na lista interna e, em seguida, limpa a lista.

        Nota:
            Se um arquivo não puder ser excluído, um log de erro será gerado, mas a função continuará
            tentando excluir os próximos arquivos da lista.
        """
        for arquivo in self._arquivos_para_excluir:
            try:
                os.remove(arquivo)
            except Exception as e:
                logger.error(
                    f"ERRO ao excluir o arquivo {arquivo}. Detalhes: {e}",
                    exc_info=True,
                )
        self._arquivos_para_excluir.clear()
