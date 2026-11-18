import numpy as np
import json
import os

from apps.Equipamentos import Var_globais

# ----------------------------------------------
# Gerar dados da simulação

def Exporta_Dados(inversor):

    Time = np.linspace(0, Var_globais.T_sim_global, Var_globais.Num_Iteracao_global)
    Curva_V_DC, Curva_I_DC, Curva_P_DC = inversor.Retornar_Val_Paineis()
    Curva_V_AC, Curva_I_AC = inversor.Resgata_forma_onda_AC()
    Curva_V_RMS_AC, Curva_I_RMS_AC = inversor.Resgata_Val_RMS_AC()
    Curva_P_Instantanea_AC, Curva_P_AC, Curva_S_AC, Curva_Q_AC = inversor.Resgata_Potencias_AC()
    V_BAT, I_BAT, P_BAT, _, SOC = inversor.Retornar_Val_Baterias()
    P_Demandada, Q_Demandada = inversor.Retornar_Val_Carga_demandada()

    # print(f"Time = {type(Time)}")
    # print(f"V_Baterias = {type(V_BAT)}")
    # print(f"I_Baterias = {type(I_BAT)}")
    # print(f"P_Baterias = {type(P_BAT)}")
    # print(f"SOC = {type(SOC)}")

    # print(f"P_Demandada = {type(P_Demandada)}")
    # print(f"Q_Demandada = {type(Q_Demandada)}")

    # print(f"V_Paineis = {type(Curva_V_DC)}")
    # print(f"I_Paineis = {type(Curva_I_DC)}")
    # print(f"P_Paineis = {type(Curva_P_DC)}")

    # print(f"saida_P_Instantanea_AC = {type(Curva_P_Instantanea_AC)}")
    # print(f"saida_P_AC = {type(Curva_P_AC)}")
    # print(f"saida_S_AC = {type(Curva_S_AC)}")
    # print(f"saida_Q_AC = {type(Curva_Q_AC)}")
    # print(f"saida_V_AC = {type(Curva_V_AC)}")
    # print(f"saida_I_AC = {type(Curva_I_AC)}")
    # print(f"saida_V_RMS_AC = {type(Curva_V_RMS_AC)}")
    # print(f"saida_I_RMS_AC = {type(Curva_I_RMS_AC)}")

    # ----------------------------------------------
    # Organizar os dados para salvar no JSON
    resultado = {
        "Curva_T_simulacao": Time.tolist(),
        "Painel_PV": {
            "Curva_V_DC": Curva_V_DC,
            "Curva_I_DC": Curva_I_DC,
            "Curva_P_DC": Curva_P_DC,
        },
        "Inversor_AC": {
            "Curva_V_AC": Curva_V_AC,
            "Curva_I_AC": Curva_I_AC,
            "Curva_V_RMS_AC": Curva_V_RMS_AC,
            "Curva_I_RMS_AC": Curva_I_RMS_AC,
        },
        "Potencias_AC": {
            "Curva_P_Instantanea_AC": Curva_P_Instantanea_AC,
            "Curva_P_AC": Curva_P_AC,
            "Curva_S_AC": Curva_S_AC,
            "Curva_Q_AC": Curva_Q_AC,
        },
        "Baterias": {
            "V_BAT": V_BAT,
            "I_BAT": I_BAT,
            "P_BAT": P_BAT,
            "SOC": SOC
        },
        "Carga_Demandada": {
            "P_Demandada": P_Demandada,
            "Q_Demandada": Q_Demandada
        }
    }

    # ----------------------------------------------
    # Definir o caminho do JSON de saída
    base_dir = os.getcwd()
    json_path = os.path.join(base_dir, "Arquivos_Temp_Json")

    output_dir = os.path.join(json_path, "Resultados_Simulacao")
    os.makedirs(output_dir, exist_ok=True)  # cria a pasta se não existir

    output_path = os.path.join(output_dir, "resultado.json")

    # ----------------------------------------------
    # Salvar como JSON
    with open(output_path, "w") as json_file:
        json.dump(resultado, json_file, indent=2)

    print(f"Resultados salvos em: {output_path}")
