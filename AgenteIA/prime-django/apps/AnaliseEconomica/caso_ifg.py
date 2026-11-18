"""
Caso IFG - Instituto Federal de Goiás
Análise de microrrede existente com sistema fotovoltaico de 254 kWp
Avaliação da adição de BESS de 500 kWh
Sem uso de gerador diesel
"""

import numpy as np
import matplotlib.pyplot as plt
from apps.AnaliseEconomica.tarifas_aneel import TarifasANEEL
from apps.AnaliseEconomica.perfil_carga import PerfilCarga
from apps.AnaliseEconomica.fotovoltaico import Painel_Fotovoltaico


class CasoIFG:
    """
    Análise financeira para o caso IFG
    - PV existente: 254 kWp
    - BESS proposto: 500 kWh
    - Sem gerador diesel
    """
    
    def __init__(self, distribuidora='EQUATORIAL GO', modalidade='verde', estrategia_bess='solar',
                 bess_carregamento_inicio=0, bess_carregamento_fim=5, icms=0.0, pis=0.0,
                 aplicar_impostos_exportacao=False, perfil_carga_csv='perfil_carga_ifg.csv',
                 escala_carga=1.0):
        """
        Inicializa análise do Caso IFG
        
        Parâmetros:
        -----------
        distribuidora : str
            Nome da distribuidora
        modalidade : str
            'azul' ou 'verde'
        estrategia_bess : str
            'solar' (carrega com PV durante o dia) ou 'madrugada' (carrega na madrugada)
        bess_carregamento_inicio : int
            Hora inicial do carregamento na madrugada (0-23)
        bess_carregamento_fim : int
            Hora final do carregamento na madrugada (0-23)
        icms : float
            Aliquota de ICMS aplicada sobre energia (ex: 0.17 = 17%)
        pis : float
            Aliquota de PIS aplicada sobre energia (ex: 0.05 = 5%)
        aplicar_impostos_exportacao : bool
            Se True, aplica impostos tambem sobre o valor da exportacao
        perfil_carga_csv : str
            Caminho para CSV da curva de carga usada na simulacao.
        escala_carga : float
            Fator multiplicador da curva de carga.
        """
        print("=" * 90)
        print(" " * 30 + "CASO IFG")
        print(" " * 20 + "Instituto Federal de Goiás")
        print("=" * 90)
        
        # Configuração do sistema existente
        self.pv_potencia_kwp = 324  # kWp instalado (ampliado de 254 para 324)
        # BESS de 500 kWh/dia (energia total processada por dia)
        # Considerando ciclo de 1x por dia: 500 kWh de capacidade
        self.bess_capacidade_kwh = 500  # kWh
        self.bess_potencia_kw = 230  # kW (mantém potência adequada para ponta)
        self.usar_diesel = False
        self.estrategia_bess = estrategia_bess
        self.bess_carregamento_inicio = bess_carregamento_inicio
        self.bess_carregamento_fim = bess_carregamento_fim
        self.icms = icms
        self.pis = pis
        self.aplicar_impostos_exportacao = aplicar_impostos_exportacao
        self.escala_carga = escala_carga
        
        print("\n⚡ CONFIGURAÇÃO DO SISTEMA:")
        print(f"  Sistema Fotovoltaico:  {self.pv_potencia_kwp} kWp (existente)")
        print(f"  BESS:                  {self.bess_capacidade_kwh} kWh / {self.bess_potencia_kw} kW (proposto)")
        print("  Gerador Diesel:        Não utilizado")
        if self.estrategia_bess == 'madrugada':
            print("  Estrategia BESS:       Carregamento na madrugada (fora ponta)")
            print(f"  Janela madrugada:      {self.bess_carregamento_inicio:02d}h - {self.bess_carregamento_fim:02d}h")
        else:
            print("  Estrategia BESS:       Carregamento com PV (durante o dia)")
        print(f"  ICMS/PIS:              {self.icms*100:.1f}% / {self.pis*100:.1f}%")
        print(f"  Impostos exportacao:   {'Sim' if self.aplicar_impostos_exportacao else 'Nao'}")
        print(f"  Escala de carga:       {self.escala_carga:.3f}x")

        # Carregar tarifas
        print(f"\n📊 Carregando tarifas da {distribuidora} - Modalidade {modalidade.upper()}...")
        self.tarifas_aneel = TarifasANEEL(distribuidora, usar_api=True)
        self.modalidade = modalidade

        if modalidade == 'azul':
            self.tarifas = self.tarifas_aneel.get_tarifas_azul()
        else:
            self.tarifas = self.tarifas_aneel.get_tarifas_verde()

        # Carregar perfil de carga específico do IFG
        self.perfil_carga_csv = perfil_carga_csv
        print(f"\n📈 Carregando perfil de carga: {self.perfil_carga_csv}...")
        self.perfil = PerfilCarga(self.perfil_carga_csv)

        # Configurar sistema PV
        self._configurar_pv()

        print("\n✅ Inicialização completa!")

    def _is_periodo_madrugada(self, hora):
        """Retorna True se a hora estiver dentro da janela de carregamento na madrugada."""
        if self.bess_carregamento_inicio <= self.bess_carregamento_fim:
            return self.bess_carregamento_inicio <= hora <= self.bess_carregamento_fim
        return hora >= self.bess_carregamento_inicio or hora <= self.bess_carregamento_fim
    
    def _configurar_pv(self):
        """Configura modelo de painel fotovoltaico"""
        # Painel Canadian Solar 610W
        self.pv_painel = Painel_Fotovoltaico(
            fabricante_painel="Canadian Solar",
            modelo_painel="CS6.2-66TB-610",
            Pmp=610,
            Isc=15.97,
            Voc=48,
            Imp=14.96,
            Vmp=40.8,
            Uisc=0.05,
            Uvoc=-0.25,
            Upmp=-0.29,
            material_painel="Silicio",
            eficiencia=22.6
        )
        
        # Número de painéis: 324 kWp / 0.610 kWp = ~531 painéis
        self.num_paineis = int(self.pv_potencia_kwp / 0.610)
        print(f"  Painéis: {self.num_paineis} × 610 Wp = {self.num_paineis * 0.610:.1f} kWp")
    
    def calcular_potencia_pv(self, hora, temperatura_C=25):
        """
        Calcula potência PV para uma hora específica
        
        Parâmetros:
        -----------
        hora : int
            Hora do dia (0-23)
        temperatura_C : float
            Temperatura ambiente
            
        Retorna:
        --------
        float : Potência em kW
        """
        # Perfil de irradiância simplificado (W/m²)
        if hora < 6 or hora >= 18:
            irradiancia = 0
        else:
            # Curva senoidal entre 6h e 18h
            angulo = (hora - 6) * np.pi / 12
            irradiancia = 1000 * np.sin(angulo)
        
        if irradiancia <= 0:
            return 0.0
        
        # Gerar curva I-V
        V_array, I_array = self.pv_painel.PV_Param.Gerar_curva_IV(temperatura_C, irradiancia)
        P_array = np.array(V_array) * np.array(I_array)
        P_max_por_painel = np.max(P_array)  # Watts
        
        # Potência total com perdas
        perdas = self.pv_painel.PV_Param.Retorna_perdas()
        P_total_kw = (P_max_por_painel * self.num_paineis * (1 - perdas)) / 1000
        
        # Eficiência do inversor
        P_total_kw *= 0.98
        
        return P_total_kw
    
    def calcular_tarifa_horaria(self, hora, dia_semana=0):
        """
        Calcula tarifa total para uma hora específica
        
        Parâmetros:
        -----------
        hora : int
            Hora do dia (0-23)
        dia_semana : int
            0-4 = dia útil, 5-6 = fim de semana
            
        Retorna:
        --------
        float : Tarifa em R$/kWh
        """
        is_ponta = TarifasANEEL.is_horario_ponta(hora, dia_semana)
        
        if self.modalidade == 'azul':
            if is_ponta:
                tarifa = self.tarifas['tusd_ponta_consumo'] + self.tarifas['te_ponta']
            else:
                tarifa = self.tarifas['tusd_fora_ponta_consumo'] + self.tarifas['te_fora_ponta']
        else:  # verde
            if is_ponta:
                tarifa = self.tarifas['tusd_ponta_consumo'] + self.tarifas['te_ponta']
            else:
                tarifa = self.tarifas['tusd_fora_ponta_consumo'] + self.tarifas['te_fora_ponta']
        
        return tarifa
    
    def simular_dia(self, dia_semana=0):
        """
        Simula operação da microrrede por 24 horas
        
        Parâmetros:
        -----------
        dia_semana : int
            0-4 = dia útil, 5-6 = fim de semana
            
        Retorna:
        --------
        dict : Resultados horários
        """
        horas = np.arange(24)
        
        # Estado do BESS (SOC - State of Charge em kWh)
        soc_bess = self.bess_capacidade_kwh * 0.1  # Iniciar descarregado (10%)
        soc_min = self.bess_capacidade_kwh * 0.1   # Mínimo 10%
        soc_max = self.bess_capacidade_kwh * 0.95  # Máximo 95%
        
        resultados = {
            'hora': [],
            'demanda_kw': [],
            'geracao_pv_kw': [],
            'potencia_bess_kw': [],  # Positivo=descarga, Negativo=carga
            'soc_bess_kwh': [],
            'energia_rede_kw': [],  # Positivo=compra, Negativo=venda
            'tarifa_kwh': [],
            'custo_hora': [],
            'is_ponta': []
        }
        
        for hora in horas:
            # Demanda
            demanda_kw = self.perfil.get_demanda(hora, dia_semana) * self.escala_carga
            
            # Geração PV
            temperatura = 25 + 10 * np.sin((hora - 6) * np.pi / 12)
            temperatura = np.clip(temperatura, 15, 35)
            geracao_pv_kw = self.calcular_potencia_pv(hora, temperatura)
            
            # Verificar se é horário de ponta
            is_ponta = TarifasANEEL.is_horario_ponta(hora, dia_semana)
            
            # Balanço energético
            saldo = geracao_pv_kw - demanda_kw
            
            # =========================================================================
            # ESTRATÉGIA DE CONTROLE DO BESS - CASO IFG
            # - Solar (padrao): carrega com PV durante o dia, descarrega na ponta
            # - Madrugada: carrega fora ponta na madrugada, nao carrega com PV
            # =========================================================================
            potencia_bess_kw = 0
            energia_rede_kw = 0
            
            # Definir horários
            periodo_preparacao_ponta = (hora >= 14 and hora <= 17)  # 14h às 17h
            periodo_carregamento = (hora >= 8 and hora <= 17)  # Período principal de carregamento
            
            if self.estrategia_bess == 'madrugada':
                periodo_madrugada = self._is_periodo_madrugada(hora)

                if saldo > 0:
                    # ===== EXCESSO DE GERAÇÃO PV =====
                    # Nao carregar com PV neste modo, exportar tudo
                    energia_rede_kw = -saldo
                else:
                    # ===== DÉFICIT DE GERAÇÃO =====
                    deficit = abs(saldo)

                    if is_ponta:
                        # ========== HORÁRIO DE PONTA (18h-21h) ==========
                        # DESCARREGAR BESS ao máximo (evitar tarifa cara)
                        energia_descarregar = min(deficit, self.bess_potencia_kw)
                        energia_descarregar = min(energia_descarregar, (soc_bess - soc_min))

                        if energia_descarregar > 0:
                            potencia_bess_kw = energia_descarregar  # Positivo = descarga
                            soc_bess -= energia_descarregar / 0.95  # 95% eficiência
                            deficit -= energia_descarregar

                        if deficit > 0:
                            energia_rede_kw = deficit

                    else:
                        # Fora da ponta: atender demanda pela rede
                        energia_rede_kw = deficit

                        # ========== CARREGAMENTO NA MADRUGADA ==========
                        if periodo_madrugada:
                            espaco_disponivel = soc_max - soc_bess

                            # Estimar demanda esperada na ponta (18h-21h)
                            energia_necessaria_ponta = 410  # kWh (margem de segurança + perdas)

                            if espaco_disponivel > 0 and soc_bess < energia_necessaria_ponta:
                                energia_alvo = energia_necessaria_ponta - soc_bess
                                energia_alvo = min(energia_alvo, espaco_disponivel)
                                horas_ate_ponta = max(18 - hora, 1)

                                taxa_carregamento = energia_alvo / horas_ate_ponta
                                taxa_carregamento = min(taxa_carregamento, self.bess_potencia_kw * 0.6)
                                energia_carregar = min(taxa_carregamento, espaco_disponivel)

                                if energia_carregar > 0:
                                    potencia_bess_kw = -energia_carregar  # Negativo = carga
                                    soc_bess += energia_carregar * 0.95  # 95% eficiência
                                    energia_rede_kw += energia_carregar  # Comprar da rede
            else:
                if saldo > 0:
                    # ===== EXCESSO DE GERAÇÃO PV =====

                    if is_ponta:
                        # ========== HORÁRIO DE PONTA: PRIORIZAR EXPORTAÇÃO ==========
                        energia_rede_kw = -saldo  # Negativo = exportação

                    else:
                        # ========== FORA DE PONTA: CARREGAR BESS PARA USAR NA PONTA ==========
                        if (soc_bess < soc_max):
                            # CARREGAR BESS com excesso de PV (prioridade)
                            espaco_disponivel = soc_max - soc_bess
                            horas_ate_ponta = max(18 - hora, 1)

                            # Taxa para encher gradualmente até às 18h
                            taxa_carregamento = espaco_disponivel / horas_ate_ponta

                            # Limitar pela potência do BESS
                            if periodo_preparacao_ponta:
                                # 14h-17h: pode usar até 80% da potência
                                taxa_carregamento = min(taxa_carregamento * 1.5, self.bess_potencia_kw * 0.8)
                            else:
                                # 6h-13h: usar até 40% da potência (carregamento lento)
                                taxa_carregamento = min(taxa_carregamento, self.bess_potencia_kw * 0.4)

                            energia_carregar = min(saldo, taxa_carregamento, espaco_disponivel)

                            if energia_carregar > 0:
                                potencia_bess_kw = -energia_carregar  # Negativo = carga
                                soc_bess += energia_carregar * 0.95  # 95% eficiência de carga
                                saldo -= energia_carregar

                        # Excedente vai para a rede (exportação fora ponta = R$ 0,19/kWh)
                        if saldo > 0:
                            energia_rede_kw = -saldo  # Negativo = exportação

                else:
                    # ===== DÉFICIT DE GERAÇÃO =====
                    deficit = abs(saldo)

                    if is_ponta:
                        # ========== HORÁRIO DE PONTA (18h-21h) ==========
                        # DESCARREGAR BESS ao máximo (evitar tarifa cara)
                        energia_descarregar = min(deficit, self.bess_potencia_kw)
                        energia_descarregar = min(energia_descarregar, (soc_bess - soc_min))

                        if energia_descarregar > 0:
                            potencia_bess_kw = energia_descarregar  # Positivo = descarga
                            soc_bess -= energia_descarregar / 0.95  # 95% eficiência
                            deficit -= energia_descarregar

                        if deficit > 0:
                            energia_rede_kw = deficit

                    elif periodo_carregamento and not is_ponta:
                        # ========== PERÍODO DE CARREGAMENTO (8h-17h) - FORA DA PONTA ==========
                        # Primeiro, atender a demanda
                        energia_rede_kw = deficit

                        # Calcular quanto falta para encher o BESS
                        espaco_disponivel = soc_max - soc_bess

                        # Estimar demanda esperada na ponta (18h-21h)
                        energia_necessaria_ponta = 410  # kWh (margem de segurança + perdas)

                        if (periodo_preparacao_ponta and
                            soc_bess < energia_necessaria_ponta and
                            espaco_disponivel > 20):

                            # Carregar o NECESSÁRIO para cobrir ponta
                            energia_alvo = energia_necessaria_ponta - soc_bess
                            energia_alvo = min(energia_alvo, espaco_disponivel)
                            horas_ate_ponta = max(18 - hora, 1)

                            # Taxa de carregamento: encher até a ponta
                            taxa_carregamento = energia_alvo / horas_ate_ponta

                            # Limitar por potência do BESS (50-70%)
                            taxa_carregamento = min(taxa_carregamento, self.bess_potencia_kw * 0.6)
                            energia_carregar = min(taxa_carregamento, espaco_disponivel)

                            if energia_carregar > 0:
                                potencia_bess_kw = -energia_carregar  # Negativo = carga
                                soc_bess += energia_carregar * 0.95  # 95% eficiência
                                energia_rede_kw += energia_carregar  # Comprar da rede

                    else:
                        # ========== NOITE/MADRUGADA (fora sol e fora ponta) ==========
                        # NÃO carregar, apenas comprar da rede para demanda
                        energia_rede_kw = deficit
            
            # Tarifa e custo
            tarifa = self.calcular_tarifa_horaria(hora, dia_semana)
            
            # Custo/receita com a rede
            if energia_rede_kw > 0:
                # Comprando da rede
                tarifa_com_impostos = tarifa * (1 + self.icms + self.pis)
                custo_hora = energia_rede_kw * tarifa_com_impostos
            else:
                # Vendendo para a rede (compensação)
                # IMPORTANTE: A compensação é MENOR que a tarifa de compra
                # Ref: Lei 14.300/2022 - Sistema de Compensação de Energia Elétrica
                
                # Para sistemas maiores que 75 kW, a compensação é reduzida
                # Usando aproximação conservadora: 90% da tarifa de compra
                # Isso reflete melhor a realidade da compensação de energia
                fator_compensacao = 0.90  # 90% da tarifa de compra
                
                # Verificar se existe tarifa SCEE na API (mas aplicar fator de correção)
                scee = self.tarifas_aneel.dados_tarifa.get('scee', {})
                scee_modalidade = scee.get(self.modalidade.lower(), {})
                
                if scee_modalidade:
                    # Mesmo que SCEE exista na API, aplicar fator de compensação realista
                    if is_ponta:
                        tarifa_base = scee_modalidade.get('te_ponta', 0) + scee_modalidade.get('tusd_ponta', 0)
                    else:
                        tarifa_base = scee_modalidade.get('te_fora_ponta', 0) + scee_modalidade.get('tusd_fora_ponta', 0)
                    
                    # Aplicar fator de compensação (energia exportada vale menos)
                    if tarifa_base > 0:
                        tarifa_venda = tarifa_base * fator_compensacao
                    else:
                        tarifa_venda = tarifa * fator_compensacao
                else:
                    # Compensação padrão: 90% da tarifa de consumo
                    tarifa_venda = tarifa * fator_compensacao
                
                if self.aplicar_impostos_exportacao:
                    tarifa_venda = tarifa_venda * (1 + self.icms + self.pis)
                custo_hora = energia_rede_kw * tarifa_venda  # energia_rede_kw é negativo, então custo será negativo (receita)
            
            # Armazenar resultados
            resultados['hora'].append(hora)
            resultados['demanda_kw'].append(demanda_kw)
            resultados['geracao_pv_kw'].append(geracao_pv_kw)
            resultados['potencia_bess_kw'].append(potencia_bess_kw)
            resultados['soc_bess_kwh'].append(soc_bess)
            resultados['energia_rede_kw'].append(energia_rede_kw)
            resultados['tarifa_kwh'].append(tarifa)
            resultados['custo_hora'].append(custo_hora)
            resultados['is_ponta'].append(is_ponta)
        
        return resultados
    
    def simular_mes(self):
        """
        Simula um mês completo (22 dias úteis + 8 fins de semana)
        
        Retorna:
        --------
        dict : Resultados mensais agregados
        """
        dias_uteis = 22
        fins_semana = 8
        
        # Simular dias típicos
        resultado_util = self.simular_dia(dia_semana=0)
        resultado_fds = self.simular_dia(dia_semana=6)
        
        # Totais mensais
        energia_demanda_mes = (sum(resultado_util['demanda_kw']) * dias_uteis + 
                               sum(resultado_fds['demanda_kw']) * fins_semana)
        
        energia_pv_mes = (sum(resultado_util['geracao_pv_kw']) * dias_uteis + 
                          sum(resultado_fds['geracao_pv_kw']) * fins_semana)
        
        energia_comprada_mes = (sum([e for e in resultado_util['energia_rede_kw'] if e > 0]) * dias_uteis + 
                                sum([e for e in resultado_fds['energia_rede_kw'] if e > 0]) * fins_semana)
        
        energia_vendida_mes = (sum([abs(e) for e in resultado_util['energia_rede_kw'] if e < 0]) * dias_uteis + 
                               sum([abs(e) for e in resultado_fds['energia_rede_kw'] if e < 0]) * fins_semana)
        
        custo_mes = (sum(resultado_util['custo_hora']) * dias_uteis + 
                     sum(resultado_fds['custo_hora']) * fins_semana)
        
        return {
            'energia_demanda_kwh': energia_demanda_mes,
            'energia_pv_kwh': energia_pv_mes,
            'energia_comprada_kwh': energia_comprada_mes,
            'energia_vendida_kwh': energia_vendida_mes,
            'custo_mensal': custo_mes,
            'resultado_dia_util': resultado_util,
            'resultado_fim_semana': resultado_fds
        }
    
    def calcular_cenario_sem_bess(self):
        """
        Calcula custos do cenário SEM BESS (apenas PV)
        
        Retorna:
        --------
        dict : Resultados sem BESS
        """
        # Temporariamente desabilitar BESS
        bess_kwh_original = self.bess_capacidade_kwh
        bess_kw_original = self.bess_potencia_kw
        self.bess_capacidade_kwh = 0
        self.bess_potencia_kw = 0
        
        resultado = self.simular_mes()
        
        # Restaurar BESS
        self.bess_capacidade_kwh = bess_kwh_original
        self.bess_potencia_kw = bess_kw_original
        
        return resultado
    
    def gerar_graficos(self, resultado_dia, titulo="Dia Útil"):
        """Gera gráficos da simulação"""
        fig, axes = plt.subplots(2, 2, figsize=(16, 10))
        fig.suptitle(f'Caso IFG - {titulo} - Modalidade {self.modalidade.upper()}', 
                     fontsize=16, fontweight='bold')
        
        horas = resultado_dia['hora']
        
        # Gráfico 1: Fluxos de Energia
        ax1 = axes[0, 0]
        ax1.plot(horas, resultado_dia['demanda_kw'], 'o-', label='Demanda', linewidth=2, color='red')
        ax1.plot(horas, resultado_dia['geracao_pv_kw'], 's-', label='Geração PV', linewidth=2, color='orange')
        ax1.fill_between(horas, 0, resultado_dia['geracao_pv_kw'], alpha=0.3, color='orange')
        
        # Destacar horário de ponta
        for i, is_ponta in enumerate(resultado_dia['is_ponta']):
            if is_ponta:
                ax1.axvspan(i-0.5, i+0.5, alpha=0.1, color='red')
        
        ax1.set_xlabel('Hora do Dia', fontsize=12)
        ax1.set_ylabel('Potência (kW)', fontsize=12)
        ax1.set_title('Demanda vs Geração PV', fontsize=14, fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.set_xticks(range(0, 24, 2))
        
        # Gráfico 2: Estado do BESS
        ax2 = axes[0, 1]
        ax2.plot(horas, resultado_dia['soc_bess_kwh'], 'o-', linewidth=2, color='blue', markersize=6)
        ax2.fill_between(horas, 0, resultado_dia['soc_bess_kwh'], alpha=0.3, color='blue')
        ax2.axhline(y=self.bess_capacidade_kwh*0.9, color='r', linestyle='--', alpha=0.5, label='SOC Máx (90%)')
        ax2.axhline(y=self.bess_capacidade_kwh*0.1, color='r', linestyle='--', alpha=0.5, label='SOC Mín (10%)')
        
        ax2.set_xlabel('Hora do Dia', fontsize=12)
        ax2.set_ylabel('Energia Armazenada (kWh)', fontsize=12)
        ax2.set_title('Estado de Carga do BESS', fontsize=14, fontweight='bold')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        ax2.set_xticks(range(0, 24, 2))
        
        # Gráfico 3: Potência do BESS
        ax3 = axes[1, 0]
        cores = ['green' if p < 0 else 'red' for p in resultado_dia['potencia_bess_kw']]
        ax3.bar(horas, resultado_dia['potencia_bess_kw'], color=cores, alpha=0.7)
        ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        
        ax3.set_xlabel('Hora do Dia', fontsize=12)
        ax3.set_ylabel('Potência (kW)', fontsize=12)
        ax3.set_title('Operação do BESS (Negativo=Carga, Positivo=Descarga)', fontsize=14, fontweight='bold')
        ax3.grid(True, alpha=0.3)
        ax3.set_xticks(range(0, 24, 2))
        
        from matplotlib.patches import Patch
        legend_elements = [Patch(facecolor='green', alpha=0.7, label='Carga'),
                          Patch(facecolor='red', alpha=0.7, label='Descarga')]
        ax3.legend(handles=legend_elements)
        
        # Gráfico 4: Energia da Rede
        ax4 = axes[1, 1]
        cores_rede = ['red' if e > 0 else 'green' for e in resultado_dia['energia_rede_kw']]
        ax4.bar(horas, resultado_dia['energia_rede_kw'], color=cores_rede, alpha=0.7)
        ax4.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        
        ax4.set_xlabel('Hora do Dia', fontsize=12)
        ax4.set_ylabel('Energia (kW)', fontsize=12)
        ax4.set_title('Fluxo com a Rede (Positivo=Compra, Negativo=Venda)', fontsize=14, fontweight='bold')
        ax4.grid(True, alpha=0.3)
        ax4.set_xticks(range(0, 24, 2))
        
        legend_elements = [Patch(facecolor='red', alpha=0.7, label='Compra'),
                          Patch(facecolor='green', alpha=0.7, label='Venda')]
        ax4.legend(handles=legend_elements)
        
        plt.tight_layout()
        return fig
    
    def gerar_relatorio(self):
        """Gera relatório completo da análise"""
        print("\n" + "=" * 90)
        print(" " * 25 + "RELATÓRIO DE ANÁLISE - CASO IFG")
        print("=" * 90)
        
        # Simular cenário COM BESS
        print("\n⚡ Simulando cenário COM BESS...")
        resultado_com_bess = self.simular_mes()
        
        # Simular cenário SEM BESS
        print("⚡ Simulando cenário SEM BESS (apenas PV)...")
        resultado_sem_bess = self.calcular_cenario_sem_bess()
        
        # Resultados COM BESS
        print(f"\n📊 CENÁRIO COM BESS ({self.bess_capacidade_kwh} kWh):")
        print("-" * 90)
        print(f"  Demanda Total:           {resultado_com_bess['energia_demanda_kwh']:>12,.0f} kWh/mês")
        print(f"  Geração PV:              {resultado_com_bess['energia_pv_kwh']:>12,.0f} kWh/mês")
        print(f"  Energia Comprada:        {resultado_com_bess['energia_comprada_kwh']:>12,.0f} kWh/mês")
        print(f"  Energia Vendida:         {resultado_com_bess['energia_vendida_kwh']:>12,.0f} kWh/mês")
        print(f"  Custo Mensal:            R$ {resultado_com_bess['custo_mensal']:>12,.2f}")
        
        # Resultados SEM BESS
        print(f"\n📊 CENÁRIO SEM BESS (apenas PV {self.pv_potencia_kwp} kWp):")
        print("-" * 90)
        print(f"  Demanda Total:           {resultado_sem_bess['energia_demanda_kwh']:>12,.0f} kWh/mês")
        print(f"  Geração PV:              {resultado_sem_bess['energia_pv_kwh']:>12,.0f} kWh/mês")
        print(f"  Energia Comprada:        {resultado_sem_bess['energia_comprada_kwh']:>12,.0f} kWh/mês")
        print(f"  Energia Vendida:         {resultado_sem_bess['energia_vendida_kwh']:>12,.0f} kWh/mês")
        print(f"  Custo Mensal:            R$ {resultado_sem_bess['custo_mensal']:>12,.2f}")
        
        # Economia do BESS
        economia_mensal = resultado_sem_bess['custo_mensal'] - resultado_com_bess['custo_mensal']
        economia_anual = economia_mensal * 12
        
        print("\n💰 ECONOMIA PROPORCIONADA PELO BESS:")
        print("-" * 90)
        print(f"  Economia Mensal:         R$ {economia_mensal:>12,.2f}")
        print(f"  Economia Anual:          R$ {economia_anual:>12,.2f}")
        
        # Indicadores financeiros
        custo_bess = self.bess_capacidade_kwh * 1900  # R$/kWh
        payback_simples = custo_bess / economia_anual if economia_anual > 0 else float('inf')
        
        print("\n📈 INDICADORES FINANCEIROS:")
        print("-" * 90)
        print(f"  Investimento BESS:       R$ {custo_bess:>12,.2f}")
        print(f"  Payback Simples:         {payback_simples:>12,.1f} anos")
        
        # Gerar gráficos
        print("\n📈 Gerando gráficos...")
        self.gerar_graficos(resultado_com_bess['resultado_dia_util'], "Dia Útil - COM BESS")
        
        # Salvar gráfico ao invés de mostrar
        filename = f'caso_ifg_{self.modalidade}.png'
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        print(f"  ✓ Gráfico salvo em: {filename}")
        
        return {
            'com_bess': resultado_com_bess,
            'sem_bess': resultado_sem_bess,
            'economia_mensal': economia_mensal,
            'economia_anual': economia_anual,
            'investimento_bess': custo_bess,
            'payback': payback_simples
        }


def main():
    """Função principal"""
    print("\n" + "=" * 90)
    print(" " * 25 + "ANÁLISE CASO IFG")
    print("=" * 90)
    
    # Testar com modalidade VERDE
    print("\n🟢 Análise com Modalidade VERDE")
    caso_verde = CasoIFG(distribuidora='EQUATORIAL GO', modalidade='verde')
    resultado_verde = caso_verde.gerar_relatorio()
    
    # Fechar gráficos
    plt.close('all')
    
    # Resumo final
    print("\n\n" + "=" * 90)
    print(" " * 25 + "RESUMO DA ANÁLISE - CASO IFG")
    print("=" * 90)
    
    print("\n💰 ECONOMIA COM BESS:")
    print(f"  Economia Mensal:     R$ {resultado_verde['economia_mensal']:>12,.2f}")
    print(f"  Economia Anual:      R$ {resultado_verde['economia_anual']:>12,.2f}")
    
    print("\n📊 INVESTIMENTO:")
    print(f"  BESS ({caso_verde.bess_capacidade_kwh} kWh):  R$ {resultado_verde['investimento_bess']:>12,.2f}")
    print(f"  Payback Simples:     {resultado_verde['payback']:>12.1f} anos")
    
    print("\n⚡ SISTEMA:")
    print(f"  PV Instalado:        {caso_verde.pv_potencia_kwp} kWp")
    print(f"  BESS:                {caso_verde.bess_capacidade_kwh} kWh / {caso_verde.bess_potencia_kw} kW")
    print("  Modalidade:          VERDE (Grupo A4)")
    
    print("\n" + "=" * 90)


if __name__ == "__main__":
    main()
