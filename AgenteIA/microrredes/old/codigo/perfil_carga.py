"""
Módulo para gerenciar perfis de carga horária
Permite carregar e interpolar demanda hora a hora
"""

import pandas as pd
import numpy as np
from pathlib import Path


class PerfilCarga:
    """
    Gerenciador de perfil de carga horária
    Carrega dados de arquivo CSV e fornece demanda para cada hora
    """
    
    def __init__(self, arquivo_csv='perfil_carga_horaria.csv'):
        """
        Inicializa perfil de carga a partir de arquivo CSV
        
        Parâmetros:
        -----------
        arquivo_csv : str
            Caminho para arquivo CSV com colunas: hora, demanda_kw, dia_semana
        """
        self.arquivo = arquivo_csv
        self.carregar_perfil()
    
    def carregar_perfil(self):
        """Carrega perfil de carga do arquivo CSV"""
        # Verificar se arquivo existe
        if not Path(self.arquivo).exists():
            raise FileNotFoundError(f"Arquivo '{self.arquivo}' não encontrado!")
        
        # Carregar CSV
        self.df = pd.read_csv(self.arquivo)
        
        # Validar colunas obrigatórias
        colunas_req = ['hora', 'demanda_kw', 'dia_semana']
        for col in colunas_req:
            if col not in self.df.columns:
                raise ValueError(f"Coluna '{col}' não encontrada no arquivo CSV!")
        
        # Separar perfis por tipo de dia
        self.perfil_util = self.df[self.df['dia_semana'] == 'util'].sort_values('hora')
        self.perfil_fim_semana = self.df[self.df['dia_semana'] == 'fim_semana'].sort_values('hora')
        
        # Calcular estatísticas
        self.demanda_media_util = self.perfil_util['demanda_kw'].mean()
        self.demanda_pico_util = self.perfil_util['demanda_kw'].max()
        self.demanda_minima_util = self.perfil_util['demanda_kw'].min()
        
        self.demanda_media_fim_semana = self.perfil_fim_semana['demanda_kw'].mean()
        self.demanda_pico_fim_semana = self.perfil_fim_semana['demanda_kw'].max()
        self.demanda_minima_fim_semana = self.perfil_fim_semana['demanda_kw'].min()
    
    def get_demanda(self, hora, dia_semana=0):
        """
        Retorna demanda para determinada hora e tipo de dia
        
        Parâmetros:
        -----------
        hora : int
            Hora do dia (0-23)
        dia_semana : int
            0-4 = dias úteis, 5-6 = fim de semana
            
        Retorna:
        --------
        float : Demanda em kW
        """
        # Validar hora
        if not 0 <= hora <= 23:
            raise ValueError(f"Hora deve estar entre 0 e 23. Recebido: {hora}")
        
        # Selecionar perfil apropriado
        if dia_semana <= 4:  # Dia útil
            perfil = self.perfil_util
        else:  # Fim de semana
            perfil = self.perfil_fim_semana
        
        # Buscar demanda para a hora
        demanda_row = perfil[perfil['hora'] == hora]
        
        if len(demanda_row) == 0:
            raise ValueError(f"Demanda para hora {hora} não encontrada no perfil!")
        
        return float(demanda_row['demanda_kw'].iloc[0])
    
    def get_perfil_completo_24h(self, tipo_dia='util'):
        """
        Retorna perfil completo de 24 horas
        
        Parâmetros:
        -----------
        tipo_dia : str
            'util' ou 'fim_semana'
            
        Retorna:
        --------
        pandas.DataFrame : Perfil com colunas hora e demanda_kw
        """
        if tipo_dia == 'util':
            return self.perfil_util[['hora', 'demanda_kw']].copy()
        else:
            return self.perfil_fim_semana[['hora', 'demanda_kw']].copy()
    
    def get_energia_diaria(self, tipo_dia='util'):
        """
        Calcula energia total consumida no dia (kWh)
        
        Parâmetros:
        -----------
        tipo_dia : str
            'util' ou 'fim_semana'
            
        Retorna:
        --------
        float : Energia em kWh
        """
        if tipo_dia == 'util':
            perfil = self.perfil_util
        else:
            perfil = self.perfil_fim_semana
        
        # Energia = soma das potências médias horárias (kW) * 1h
        return perfil['demanda_kw'].sum()
    
    def get_estatisticas(self):
        """Retorna estatísticas do perfil de carga"""
        return {
            'dia_util': {
                'demanda_media_kw': self.demanda_media_util,
                'demanda_pico_kw': self.demanda_pico_util,
                'demanda_minima_kw': self.demanda_minima_util,
                'energia_diaria_kwh': self.get_energia_diaria('util'),
                'fator_carga': self.demanda_media_util / self.demanda_pico_util if self.demanda_pico_util > 0 else 0
            },
            'fim_semana': {
                'demanda_media_kw': self.demanda_media_fim_semana,
                'demanda_pico_kw': self.demanda_pico_fim_semana,
                'demanda_minima_kw': self.demanda_minima_fim_semana,
                'energia_diaria_kwh': self.get_energia_diaria('fim_semana'),
                'fator_carga': self.demanda_media_fim_semana / self.demanda_pico_fim_semana if self.demanda_pico_fim_semana > 0 else 0
            }
        }
    
    def plotar_perfil(self):
        """Plota perfil de carga comparando dias úteis e fim de semana"""
        import matplotlib.pyplot as plt
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
        
        # Perfil dia útil
        ax1.plot(self.perfil_util['hora'], self.perfil_util['demanda_kw'], 
                marker='o', linewidth=2, markersize=6, color='steelblue')
        ax1.axhline(self.demanda_media_util, color='red', linestyle='--', 
                   label=f'Média: {self.demanda_media_util:.0f} kW')
        ax1.set_xlabel('Hora do Dia', fontsize=11)
        ax1.set_ylabel('Demanda (kW)', fontsize=11)
        ax1.set_title('Perfil de Carga - Dia Útil', fontsize=12, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        ax1.set_xticks(range(0, 24, 2))
        
        # Perfil fim de semana
        ax2.plot(self.perfil_fim_semana['hora'], self.perfil_fim_semana['demanda_kw'], 
                marker='s', linewidth=2, markersize=6, color='coral')
        ax2.axhline(self.demanda_media_fim_semana, color='red', linestyle='--',
                   label=f'Média: {self.demanda_media_fim_semana:.0f} kW')
        ax2.set_xlabel('Hora do Dia', fontsize=11)
        ax2.set_ylabel('Demanda (kW)', fontsize=11)
        ax2.set_title('Perfil de Carga - Fim de Semana', fontsize=12, fontweight='bold')
        ax2.grid(True, alpha=0.3)
        ax2.legend()
        ax2.set_xticks(range(0, 24, 2))
        
        plt.tight_layout()
        plt.savefig('perfil_carga.png', dpi=150, bbox_inches='tight')
        print("\n📊 Gráfico salvo: 'perfil_carga.png'")
        plt.show()
    
    def gerar_relatorio(self):
        """Gera relatório detalhado do perfil de carga"""
        stats = self.get_estatisticas()
        
        print("\n" + "=" * 90)
        print(" " * 30 + "PERFIL DE CARGA")
        print("=" * 90)
        print(f"\nArquivo: {self.arquivo}")
        
        print("\n" + "-" * 90)
        print(" DIA ÚTIL")
        print("-" * 90)
        util = stats['dia_util']
        print(f"  Demanda Média:     {util['demanda_media_kw']:6.1f} kW")
        print(f"  Demanda Pico:      {util['demanda_pico_kw']:6.1f} kW")
        print(f"  Demanda Mínima:    {util['demanda_minima_kw']:6.1f} kW")
        print(f"  Energia Diária:    {util['energia_diaria_kwh']:6.1f} kWh")
        print(f"  Fator de Carga:    {util['fator_carga']:6.1%}")
        
        print("\n" + "-" * 90)
        print(" FIM DE SEMANA")
        print("-" * 90)
        fds = stats['fim_semana']
        print(f"  Demanda Média:     {fds['demanda_media_kw']:6.1f} kW")
        print(f"  Demanda Pico:      {fds['demanda_pico_kw']:6.1f} kW")
        print(f"  Demanda Mínima:    {fds['demanda_minima_kw']:6.1f} kW")
        print(f"  Energia Diária:    {fds['energia_diaria_kwh']:6.1f} kWh")
        print(f"  Fator de Carga:    {fds['fator_carga']:6.1%}")
        
        print("\n" + "-" * 90)
        print(" RESUMO ANUAL (considerando 260 dias úteis, 105 fins de semana)")
        print("-" * 90)
        energia_anual_util = util['energia_diaria_kwh'] * 260
        energia_anual_fds = fds['energia_diaria_kwh'] * 105
        energia_anual_total = energia_anual_util + energia_anual_fds
        
        print(f"  Energia Anual (Dias Úteis):     {energia_anual_util:,.0f} kWh")
        print(f"  Energia Anual (Fins de Semana): {energia_anual_fds:,.0f} kWh")
        print(f"  Energia Anual TOTAL:            {energia_anual_total:,.0f} kWh")
        print(f"  Demanda Máxima:                 {max(util['demanda_pico_kw'], fds['demanda_pico_kw']):,.0f} kW")
        
        print("=" * 90)


def exemplo_uso_perfil():
    """Exemplo de uso da classe PerfilCarga"""
    
    # Carregar perfil
    perfil = PerfilCarga('perfil_carga_horaria.csv')
    
    # Gerar relatório
    perfil.gerar_relatorio()
    
    # Plotar gráficos
    perfil.plotar_perfil()
    
    # Exemplo de consulta pontual
    print("\n" + "=" * 90)
    print(" EXEMPLOS DE CONSULTA")
    print("=" * 90)
    
    # Demanda em diferentes horários
    print("\nDia útil:")
    for hora in [0, 6, 12, 18, 23]:
        demanda = perfil.get_demanda(hora, dia_semana=0)
        print(f"  {hora:02d}:00h - {demanda:.0f} kW")
    
    print("\nFim de semana:")
    for hora in [0, 6, 12, 18, 23]:
        demanda = perfil.get_demanda(hora, dia_semana=6)
        print(f"  {hora:02d}:00h - {demanda:.0f} kW")
    
    print("=" * 90)


if __name__ == "__main__":
    exemplo_uso_perfil()
