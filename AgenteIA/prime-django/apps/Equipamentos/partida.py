"""Intertravamento do contator de carga por pré-carga e tensão estabilizada."""


class SequenciaPartida:
    def __init__(self, tempo_estavel_s=.02, tolerancia_tensao=.02):
        self.tempo_estavel_s = tempo_estavel_s
        self.tolerancia_tensao = tolerancia_tensao
        self.estavel_desde = None
        self.conectada = False
        self.fim_precarga_s = None
        self.fechamento_s = None
        self.estado = 'pre_carga'

    def atualizar(self, t, precarga_ok, tensao_ok, protecao=False):
        if self.conectada:
            return True
        if not precarga_ok or protecao:
            self.estado = 'pre_carga' if not precarga_ok else 'bloqueada'
            self.estavel_desde = None
            return False
        if self.fim_precarga_s is None:
            self.fim_precarga_s = t
        self.estado = 'estabilizacao'
        if not tensao_ok:
            self.estavel_desde = None
        elif self.estavel_desde is None:
            self.estavel_desde = t
        elif t - self.estavel_desde >= self.tempo_estavel_s - 1e-12:
            self.conectada = True
            self.fechamento_s = t
            self.estado = 'carga_conectada'
        return self.conectada
