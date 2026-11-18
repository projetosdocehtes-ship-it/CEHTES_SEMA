import numpy as np
import pandapower as pp
import pandapower.plotting as pplot
import matplotlib.pyplot as plt
from fotovoltaico import Painel_Fotovoltaico
from perfil_carga import PerfilCarga

class MicrorrredePowerFlow:
    def __init__(self, perfil_carga_csv='perfil_carga_horaria.csv', usar_perfil_variavel=True):
        """
        Inicializa a rede pandapower com todos os componentes da microrrede
        
        Parâmetros:
        -----------
        perfil_carga_csv : str
            Caminho para arquivo CSV com perfil de carga horária
        usar_perfil_variavel : bool
            Se True, usa perfil variável. Se False, usa carga constante de 500 kW
        """
        self.net = pp.create_empty_network()
        
        # Configurar perfil de carga
        self.usar_perfil_variavel = usar_perfil_variavel
        if usar_perfil_variavel:
            try:
                self.perfil_carga = PerfilCarga(perfil_carga_csv)
            except FileNotFoundError:
                print(f"⚠️  Arquivo '{perfil_carga_csv}' não encontrado. Usando carga constante de 500 kW.")
                self.usar_perfil_variavel = False
                self.carga_p_mw = 0.5
        else:
            self.carga_p_mw = 0.5  # 500 kW constante
        
        # Criar barras
        self.bus_distribuidora = pp.create_bus(self.net, vn_kv=13.8, name="Distribuidora", geodata=(0, 0))
        self.bus_carga = pp.create_bus(self.net, vn_kv=13.8, name="Carga", geodata=(5, 0))
        self.bus_pv = pp.create_bus(self.net, vn_kv=13.8, name="PV", geodata=(5, 2))
        self.bus_bess = pp.create_bus(self.net, vn_kv=13.8, name="BESS", geodata=(5, -2))
        self.bus_diesel = pp.create_bus(self.net, vn_kv=13.8, name="Diesel", geodata=(5, -4))
        
        # Fonte externa (barra infinita da distribuidora)
        pp.create_ext_grid(self.net, bus=self.bus_distribuidora, vm_pu=0.98, name="Rede Distribuidora")
        
        # Linhas de conexão
        # 500m entre distribuidora e carga
        pp.create_line_from_parameters(self.net, from_bus=self.bus_distribuidora, to_bus=self.bus_carga,
                                       length_km=15, r_ohm_per_km=0.2, x_ohm_per_km=0.08,
                                       c_nf_per_km=10, max_i_ka=0.4, name="Linha Distribuidora-Carga")
        
        # 500m entre carga e cada gerador
        pp.create_line_from_parameters(self.net, from_bus=self.bus_carga, to_bus=self.bus_pv,
                                       length_km=0.5, r_ohm_per_km=0.2, x_ohm_per_km=0.08,
                                       c_nf_per_km=10, max_i_ka=0.4, name="Linha Carga-PV")
        
        pp.create_line_from_parameters(self.net, from_bus=self.bus_carga, to_bus=self.bus_bess,
                                       length_km=0.5, r_ohm_per_km=0.2, x_ohm_per_km=0.08,
                                       c_nf_per_km=10, max_i_ka=0.4, name="Linha Carga-BESS")
        
        pp.create_line_from_parameters(self.net, from_bus=self.bus_carga, to_bus=self.bus_diesel,
                                       length_km=0.5, r_ohm_per_km=0.2, x_ohm_per_km=0.08,
                                       c_nf_per_km=10, max_i_ka=0.4, name="Linha Carga-Diesel")

        # Carga (variável ou constante dependendo da configuração)
        # Inicializar com valor padrão, será atualizado a cada hora na simulação
        if not self.usar_perfil_variavel:
            self.carga_p_mw = 0.5  # 500 kW constante
        else:
            # Usar valor médio como inicial
            stats = self.perfil_carga.get_estatisticas()
            self.carga_p_mw = stats['dia_util']['demanda_media_kw'] / 1000  # Converter para MW
        
        self.carga_q_mvar = self.carga_p_mw * np.tan(np.arccos(0.95))
        self.load_idx = pp.create_load(self.net, bus=self.bus_carga, p_mw=self.carga_p_mw, 
                      q_mvar=self.carga_q_mvar, name="Carga Principal")
        
        # Gerador Diesel (backup, max 300 kW)
        self.diesel_idx = pp.create_sgen(self.net, bus=self.bus_diesel, p_mw=0.0, q_mvar=0.0,
                                         name="Gerador Diesel", controllable=False)
        
        # BESS (Battery Energy Storage System, max 200 kW)
        self.bess_idx = pp.create_sgen(self.net, bus=self.bus_bess, p_mw=0.0, q_mvar=0.0,
                                       name="BESS", controllable=False)
        
        # Gerador PV (será atualizado com base na irradiância e temperatura)
        self.pv_idx = pp.create_sgen(self.net, bus=self.bus_pv, p_mw=0.0, q_mvar=0.0,
                                     name="Sistema Fotovoltaico", controllable=False)
        
        # Configurar modelo fotovoltaico
        self.setup_pv_system()
        
        # Armazenar resultados
        self.resultados = {
            'hora': [],
            'p_distribuidora_mw': [],
            'q_distribuidora_mvar': [],
            'p_pv_mw': [],
            'p_bess_mw': [],
            'p_diesel_mw': [],
            'v_carga_pu': [],
            'i_carga_ka': []
        }
    
    def setup_pv_system(self):
        """Configura o sistema fotovoltaico usando a classe Painel_Fotovoltaico"""
        # Painel Canadian Solar 610W
        self.pv_painel = Painel_Fotovoltaico(
            fabricante_painel="Canadian Solar",
            modelo_painel="CS6.2-66TB-610",
            Pmp=610,      # W
            Isc=15.97,    # A
            Voc=48,       # V
            Imp=14.96,    # A
            Vmp=40.8,     # V
            Uisc=0.05,    # A/°C
            Uvoc=-0.25,   # V/°C
            Upmp=-0.29,   # %/°C
            material_painel="Silicio",
            eficiencia=22.6
        )
        
        # Número de painéis para atingir ~400 kW nominal
        # 400 kW / 0.610 kW = 656 painéis
        self.num_paineis = 656
        self.pv_potencia_nominal_kw = self.num_paineis * 0.610  # ~400 kW
    
    def calcular_potencia_pv(self, temperatura_C, irradiancia_W_m2):
        """
        Calcula a potência PV com base na temperatura e irradiância
        usando o modelo de painel fotovoltaico
        """
        if irradiancia_W_m2 <= 0:
            return 0.0
        
        # Gerar curva I-V para as condições atuais
        V_array, I_array = self.pv_painel.PV_Param.Gerar_curva_IV(temperatura_C, irradiancia_W_m2)
        
        # Calcular potência em cada ponto
        P_array = np.array(V_array) * np.array(I_array)
        
        # Encontrar ponto de máxima potência
        P_max_por_painel = np.max(P_array)  # em Watts
        
        # Potência total do sistema (considerando perdas do painel)
        perdas = self.pv_painel.PV_Param.Retorna_perdas()
        P_total_kw = (P_max_por_painel * self.num_paineis * (1 - perdas)) / 1000  # kW
        
        # Considerar eficiência do inversor (98%)
        P_total_kw *= 0.98
        
        return P_total_kw
    
    def gerar_perfil_diario(self):
        """Gera perfis de irradiância e temperatura para 24 horas"""
        horas = np.arange(0, 24)
        
        # Perfil de irradiância solar (W/m²) - curva senoidal típica de dia ensolarado
        irradiancia = np.zeros(24)
        for h in range(6, 19):  # Sol entre 6h e 18h
            # Pico ao meio-dia com 1000 W/m²
            angulo = (h - 6) * np.pi / 12
            irradiancia[h] = 1000 * np.sin(angulo)
        
        # Perfil de temperatura (°C) - varia entre 15°C (noite) e 35°C (tarde)
        temperatura = 25 + 10 * np.sin((horas - 6) * np.pi / 12)
        temperatura = np.clip(temperatura, 15, 35)
        
        return horas, irradiancia, temperatura
    
    def controle_bess_diesel(self, p_pv_mw, p_carga_mw):
        """
        Estratégia de controle simplificada para BESS e Diesel
        - Se PV > Carga: BESS carrega (negativo) ou exporta para rede
        - Se PV < Carga: BESS descarrega (positivo) ou diesel complementa
        """
        diferenca = p_carga_mw - p_pv_mw
        
        # Capacidade BESS: ±200 kW
        bess_max_mw = 0.2
        diesel_max_mw = 0.3
        
        if diferenca <= 0:
            # Excesso de geração PV
            p_bess = max(-bess_max_mw, diferenca)  # BESS carrega (negativo)
            p_diesel = 0.0
        else:
            # Déficit de geração
            if diferenca <= bess_max_mw:
                p_bess = diferenca  # BESS supre
                p_diesel = 0.0
            else:
                p_bess = bess_max_mw  # BESS no máximo
                p_diesel = min(diesel_max_mw, diferenca - bess_max_mw)
        
        return p_bess, p_diesel
    
    def simular_24h(self, dia_semana=0):
        """
        Executa simulação de fluxo de potência para 24 horas
        
        Parâmetros:
        -----------
        dia_semana : int
            0-4 = dias úteis, 5-6 = fim de semana (usado apenas se perfil variável estiver ativo)
        """
        horas, irradiancia, temperatura = self.gerar_perfil_diario()
        
        print("=" * 70)
        print("SIMULAÇÃO DE FLUXO DE POTÊNCIA - MICRORREDE 24h")
        print("=" * 70)
        print(f"Capacidade PV: {self.pv_potencia_nominal_kw:.1f} kW")
        
        if self.usar_perfil_variavel:
            tipo_dia = 'Dia Útil' if dia_semana <= 4 else 'Fim de Semana'
            stats = self.perfil_carga.get_estatisticas()
            key = 'dia_util' if dia_semana <= 4 else 'fim_semana'
            print(f"Tipo de dia: {tipo_dia}")
            print(f"Carga média: {stats[key]['demanda_media_kw']:.1f} kW")
            print(f"Carga pico: {stats[key]['demanda_pico_kw']:.1f} kW")
        else:
            print(f"Carga constante: {self.carga_p_mw * 1000:.1f} kW")
        
        print("Capacidade BESS: ±200 kW")
        print("Capacidade Diesel: 300 kW")
        print("=" * 70)
        
        for hora in horas:
            G = irradiancia[int(hora)]
            T = temperatura[int(hora)]
            
            # Atualizar carga se usar perfil variável
            if self.usar_perfil_variavel:
                demanda_kw = self.perfil_carga.get_demanda(int(hora), dia_semana)
                self.carga_p_mw = demanda_kw / 1000  # Converter para MW
                self.carga_q_mvar = self.carga_p_mw * np.tan(np.arccos(0.95))
                
                # Atualizar carga na rede
                self.net.load.at[self.load_idx, 'p_mw'] = self.carga_p_mw
                self.net.load.at[self.load_idx, 'q_mvar'] = self.carga_q_mvar
            
            # Calcular potência PV
            p_pv_kw = self.calcular_potencia_pv(T, G)
            p_pv_mw = p_pv_kw / 10000
            
            # Controlar BESS e Diesel
            p_bess_mw, p_diesel_mw = self.controle_bess_diesel(p_pv_mw, self.carga_p_mw)
            
            # Atualizar geradores na rede
            self.net.sgen.at[self.pv_idx, 'p_mw'] = p_pv_mw
            self.net.sgen.at[self.bess_idx, 'p_mw'] = p_bess_mw
            self.net.sgen.at[self.diesel_idx, 'p_mw'] = p_diesel_mw
            
            # Assumir fator de potência 1.0 para geradores (simplificação)
            self.net.sgen.at[self.pv_idx, 'q_mvar'] = 0.0
            self.net.sgen.at[self.bess_idx, 'q_mvar'] = 0.0
            self.net.sgen.at[self.diesel_idx, 'q_mvar'] = 0.0
            
            # Executar fluxo de potência
            try:
                pp.runpp(self.net, algorithm='nr', calculate_voltage_angles=True)
                
                # Coletar resultados
                p_dist = self.net.res_ext_grid.at[0, 'p_mw']
                q_dist = self.net.res_ext_grid.at[0, 'q_mvar']
                v_carga = self.net.res_bus.at[self.bus_carga, 'vm_pu']
                
                # Calcular corrente na barra da carga
                # I = S / (sqrt(3) * V) para sistema trifásico
                p_carga = self.net.res_load.at[0, 'p_mw']
                q_carga = self.net.res_load.at[0, 'q_mvar']
                s_carga = np.sqrt(p_carga**2 + q_carga**2)
                v_carga_kv = v_carga * 13.8
                i_carga_ka = s_carga / (np.sqrt(3) * v_carga_kv)
                
                self.resultados['hora'].append(hora)
                self.resultados['p_distribuidora_mw'].append(p_dist)
                self.resultados['q_distribuidora_mvar'].append(q_dist)
                self.resultados['p_pv_mw'].append(p_pv_mw)
                self.resultados['p_bess_mw'].append(p_bess_mw)
                self.resultados['p_diesel_mw'].append(p_diesel_mw)
                self.resultados['v_carga_pu'].append(v_carga)
                self.resultados['i_carga_ka'].append(i_carga_ka)
                
                print(f"Hora {int(hora):02d}:00 | G={G:6.1f} W/m² | T={T:4.1f}°C | "
                      f"PV={p_pv_mw*1000:5.1f}kW | BESS={p_bess_mw*1000:+6.1f}kW | "
                      f"Diesel={p_diesel_mw*1000:5.1f}kW | Dist={p_dist*1000:+6.1f}kW")
                
            except Exception as e:
                print(f"Erro no fluxo de potência na hora {hora}: {e}")
        
        print("=" * 70)
        print("Simulação concluída!")
        print("=" * 70)
    
    def plotar_resultados(self):
        """Plota os resultados da simulação"""
        fig, axes = plt.subplots(4, 1, figsize=(14, 12))
        
        # Gráfico 1: Potências dos geradores
        ax1 = axes[0]
        ax1.plot(self.resultados['hora'], np.array(self.resultados['p_pv_mw']) * 1000, 
                'o-', label='PV', linewidth=2, color='gold')
        ax1.plot(self.resultados['hora'], np.array(self.resultados['p_bess_mw']) * 1000, 
                's-', label='BESS (+descarga / -carga)', linewidth=2, color='green')
        ax1.plot(self.resultados['hora'], np.array(self.resultados['p_diesel_mw']) * 1000, 
                '^-', label='Diesel', linewidth=2, color='brown')
        ax1.axhline(y=self.carga_p_mw * 1000, color='red', linestyle='--', 
                   linewidth=2, label='Carga (500 kW)')
        ax1.set_xlabel('Hora do dia')
        ax1.set_ylabel('Potência (kW)')
        ax1.set_title('Geração e Carga ao Longo de 24h')
        ax1.legend(loc='best')
        ax1.grid(True, alpha=0.3)
        ax1.set_xlim([0, 23])
        
        # Gráfico 2: Potência no ponto de conexão com a distribuidora
        ax2 = axes[1]
        p_dist_kw = np.array(self.resultados['p_distribuidora_mw']) * 1000
        cores = ['red' if p > 0 else 'blue' for p in p_dist_kw]
        ax2.bar(self.resultados['hora'], p_dist_kw, color=cores, alpha=0.7, 
               label='Distribuidora (+ = compra / - = venda)')
        ax2.axhline(y=0, color='black', linestyle='-', linewidth=1)
        ax2.set_xlabel('Hora do dia')
        ax2.set_ylabel('Potência (kW)')
        ax2.set_title('Fluxo de Potência Ativa no Ponto de Conexão com Distribuidora')
        ax2.legend(loc='best')
        ax2.grid(True, alpha=0.3, axis='y')
        ax2.set_xlim([-0.5, 23.5])
        
        # Gráfico 3: Tensão na barra da carga
        ax3 = axes[2]
        ax3.plot(self.resultados['hora'], self.resultados['v_carga_pu'], 
                'o-', linewidth=2, color='purple', label='Tensão na Carga')
        ax3.axhline(y=1.0, color='green', linestyle='--', linewidth=1, label='Tensão nominal')
        ax3.axhline(y=0.95, color='orange', linestyle='--', linewidth=1, alpha=0.5)
        ax3.axhline(y=1.05, color='orange', linestyle='--', linewidth=1, alpha=0.5, 
                   label='Limites ±5%')
        ax3.set_xlabel('Hora do dia')
        ax3.set_ylabel('Tensão (p.u.)')
        ax3.set_title('Perfil de Tensão na Barra da Carga')
        ax3.legend(loc='best')
        ax3.grid(True, alpha=0.3)
        ax3.set_xlim([0, 23])
        ax3.set_ylim([0.94, 1.06])
        
        # Gráfico 4: Corrente na barra da carga
        ax4 = axes[3]
        i_carga_a = np.array(self.resultados['i_carga_ka']) * 1000  # Converter para A
        ax4.plot(self.resultados['hora'], i_carga_a, 
                'o-', linewidth=2, color='darkblue', label='Corrente na Carga')
        ax4.set_xlabel('Hora do dia')
        ax4.set_ylabel('Corrente (A)')
        ax4.set_title('Perfil de Corrente na Barra da Carga')
        ax4.legend(loc='best')
        ax4.grid(True, alpha=0.3)
        ax4.set_xlim([0, 23])
        
        plt.tight_layout()
        plt.savefig('resultados_microrrede.png', dpi=150, bbox_inches='tight')
        print("\nGráfico salvo como 'resultados_microrrede.png'")
        plt.show()
    
    def gerar_diagrama_unifilar(self):
        """Gera o diagrama unifilar da microrrede"""
        try:
            import pandapower.plotting as pplot
            
            # Executar fluxo de potência inicial para ter dados
            # Configurar geradores com valores nominais
            self.net.sgen.at[self.pv_idx, 'p_mw'] = 0.3
            self.net.sgen.at[self.bess_idx, 'p_mw'] = 0.0
            self.net.sgen.at[self.diesel_idx, 'p_mw'] = 0.2
            pp.runpp(self.net, numba=False)
            
            # Criar figura para o diagrama
            fig, ax = plt.subplots(1, 1, figsize=(16, 12))
            
            # Plotar usando a função simple_plot
            pplot.simple_plot(self.net, plot_loads=True, plot_sgens=True, 
                             load_size=2.0, sgen_size=2.0, ext_grid_size=2.5,
                             bus_size=1.5, line_width=2.0,
                             show_plot=False, ax=ax)
            
            # Adicionar labels nas barras
            for idx in self.net.bus.index:
                bus_name = self.net.bus.at[idx, 'name']
                geo_str = self.net.bus.at[idx, 'geo']
                # Extrair coordenadas do formato {"coordinates":[x,y], "type":"Point"}
                import json
                geo_dict = json.loads(geo_str)
                x, y = geo_dict['coordinates']
                
                # Colocar o nome acima da barra
                ax.text(x, y + 0.4, bus_name, 
                       ha='center', va='bottom', fontsize=11, 
                       fontweight='bold', color='darkblue',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', 
                                alpha=0.7, edgecolor='darkblue'))
            
            # Adicionar labels nos geradores
            for idx in self.net.sgen.index:
                sgen_name = self.net.sgen.at[idx, 'name']
                sgen_bus = self.net.sgen.at[idx, 'bus']
                geo_str = self.net.bus.at[sgen_bus, 'geo']
                import json
                geo_dict = json.loads(geo_str)
                x, y = geo_dict['coordinates']
                
                # Colocar o nome do gerador ao lado
                ax.text(x + 0.8, y, sgen_name, 
                       ha='left', va='center', fontsize=9, 
                       color='green', style='italic')
            
            # Adicionar label na carga
            for idx in self.net.load.index:
                load_name = self.net.load.at[idx, 'name']
                load_bus = self.net.load.at[idx, 'bus']
                geo_str = self.net.bus.at[load_bus, 'geo']
                import json
                geo_dict = json.loads(geo_str)
                x, y = geo_dict['coordinates']
                
                # Colocar o nome da carga ao lado
                ax.text(x + 0.8, y, f"{load_name}\n500 kW", 
                       ha='left', va='center', fontsize=9, 
                       color='darkorange', style='italic')
            
            # Adicionar label na distribuidora
            geo_str = self.net.bus.at[self.bus_distribuidora, 'geo']
            import json
            geo_dict = json.loads(geo_str)
            x_dist, y_dist = geo_dict['coordinates']
            ax.text(x_dist - 0.8, y_dist, 
                   "REDE\nCONCESSIONÁRIA\n13.8 kV\n0.98 pu", 
                   ha='right', va='center', fontsize=10, 
                   color='darkred', fontweight='bold',
                   bbox=dict(boxstyle='round,pad=0.4', facecolor='lightcoral', 
                            alpha=0.8, edgecolor='darkred', linewidth=2))
            
            ax.set_title('Diagrama Unifilar da Microrrede', fontsize=16, fontweight='bold', pad=20)
            ax.grid(True, alpha=0.2)
            
            plt.tight_layout()
            plt.savefig('diagrama_unifilar.png', dpi=200, bbox_inches='tight')
            print("Diagrama unifilar salvo como 'diagrama_unifilar.png'")
            plt.show()
            
        except ImportError as e:
            print(f"Erro: pandapower.plotting não disponível - {e}")
        except Exception as e:
            print(f"Erro ao gerar diagrama unifilar: {e}")
    
    def gerar_relatorio(self):
        """Gera relatório resumido da simulação"""
        p_dist = np.array(self.resultados['p_distribuidora_mw']) * 1000  # kW
        
        energia_comprada = np.sum(p_dist[p_dist > 0])  # kWh (considerando 1h por step)
        energia_vendida = np.sum(np.abs(p_dist[p_dist < 0]))  # kWh
        
        print("\n" + "=" * 70)
        print("RELATÓRIO RESUMIDO")
        print("=" * 70)
        print(f"Energia total comprada da distribuidora: {energia_comprada:.2f} kWh")
        print(f"Energia total vendida para distribuidora: {energia_vendida:.2f} kWh")
        print(f"Balanço energético: {energia_comprada - energia_vendida:.2f} kWh")
        print(f"Energia gerada pelo PV: {np.sum(self.resultados['p_pv_mw']) * 1000:.2f} kWh")
        print(f"Energia consumida pela carga: {self.carga_p_mw * 1000 * 24:.2f} kWh")
        print("=" * 70)


if __name__ == "__main__":
    # Criar e simular microrrede
    microrrede = MicrorrredePowerFlow()
    
    # Gerar diagrama unifilar
    print("\n" + "=" * 70)
    print("GERANDO DIAGRAMA UNIFILAR")
    print("=" * 70)
    microrrede.gerar_diagrama_unifilar()
    
    # Simular fluxo de potência
    microrrede.simular_24h()
    microrrede.gerar_relatorio()
    microrrede.plotar_resultados()
