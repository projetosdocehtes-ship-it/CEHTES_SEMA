"""Balanço médio CC/CA com reserva capacitiva finita e auditável."""
import math
import numpy as np


class EloCC:
    def __init__(self, *, capacitancia_f, tensao_nominal_v, tensao_min_v, tensao_max_v, tensao_inicial_v, tempo_recomposicao_s):
        valores = [capacitancia_f, tensao_nominal_v, tensao_min_v, tensao_max_v, tempo_recomposicao_s]
        if not all(math.isfinite(v) and v > 0 for v in valores) or not 0 <= tensao_inicial_v <= tensao_max_v or not tensao_min_v < tensao_nominal_v <= tensao_max_v:
            raise ValueError('Parâmetros inválidos para o elo CC.')
        self.c = capacitancia_f
        self.e_min = .5 * self.c * tensao_min_v ** 2
        self.e_max = .5 * self.c * tensao_max_v ** 2
        self.e_ref = .5 * self.c * tensao_nominal_v ** 2
        self.energia = .5 * self.c * tensao_inicial_v ** 2
        self.energia_inicial = self.energia
        self.tau = tempo_recomposicao_s

    @property
    def recomposicao_w(self):
        return (self.e_ref - self.energia) / self.tau

    def potencia_disponivel(self, p_dc_w, dt):
        if dt <= 0:
            raise ValueError('Passo do elo CC deve ser positivo.')
        return max(0.0, p_dc_w + max(0.0, self.energia - self.e_min) / dt)

    def atualizar(self, p_dc_w, p_ac_w, eficiencia, dt, limite_recarga_w=None):
        antes = self.energia
        candidata = antes + (p_dc_w - p_ac_w / eficiencia) * dt
        piso = self.e_min if antes >= self.e_min or p_ac_w > 1e-7 else 0.0
        if candidata < piso - 1e-7:
            raise ValueError('Elo CC esgotado: consumo CC excede energia disponível.')
        teto = min(self.e_max, antes + limite_recarga_w * dt) if limite_recarga_w is not None else self.e_max
        excedente_w = max(0.0, (candidata - teto) / dt)
        self.energia = min(teto, max(piso, candidata))
        p_elo_w = (antes - self.energia) / dt  # positivo: fornece energia
        erro_j = (p_dc_w + p_elo_w - p_ac_w / eficiencia - excedente_w) * dt
        return {'energia_j': self.energia, 'tensao_v': math.sqrt(2 * self.energia / self.c),
                'potencia_w': p_elo_w, 'excedente_w': excedente_w, 'erro_j': erro_j}


def limitar_saida(onda, rms, *, p_dc, demanda, eficiencia, potencia_nominal_w, corrente_max, fases, fp):
    if not 0 < eficiencia <= 1 or not 0 < fp <= 1:
        raise ValueError('Eficiência e fator de potência devem estar entre 0 e 1.')
    fator_fases = math.sqrt(3) if fases > 1 else 1
    if demanda <= 0:
        # Inversor energizado a vazio: corrente zero não significa tensão zero.
        return np.array([onda[0], 0.0]), np.array([rms[0], 0.0])
    p_calculada = fator_fases * abs(rms[0] * rms[1]) * fp
    limite = max(0, min(max(p_dc, 0) * eficiencia, demanda, potencia_nominal_w))
    escala = math.sqrt(min(1, limite / p_calculada)) if p_calculada > 0 else 0
    if abs(rms[1]) > 0:
        escala = min(escala, corrente_max / abs(rms[1]))
    return np.asarray(onda) * escala, np.asarray(rms) * escala
