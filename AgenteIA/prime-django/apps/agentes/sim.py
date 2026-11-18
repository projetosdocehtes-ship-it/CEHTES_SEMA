import Agentes
import Classes
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
from Var_globais import Iteracao_Sim, T_sim, data, nome_cidade, pais


def executar_simulacao(
    pmp,
    isc,
    voc,
    imp,
    vmp,
    uisc,
    uvoc,
    upmp,
    material_painel,
    eficiencia_painel,
    nm_paineis,
    nm_mppt,
    in_pmax,
    imax_mppt,
    in_vnom,
    in_vmin,
    in_vmax,
    in_mpp_vmin,
    in_mpp_vmax,
    out_pmax,
    out_imax,
    out_vnom,
    out_freq,
    eficiencia_inv,
    max_thd,
    fator_potencia,
):
    st.info("🚀 Iniciando simulação do sistema fotovoltaico...")

    # ------------------------------------------- Criando Equipamentos -------------------------------------------
    st.write("🔧 Criando o Painel Fotovoltaico...")
    painel = Classes.Painel_Fotovoltaico(
        pmp, isc, voc, imp, vmp, uisc, uvoc, upmp, material_painel, eficiencia_painel
    )

    st.write("🔧 Criando o Inversor...")
    inversor = Classes.Inversor_DC_AC(
        nm_mppt,
        in_pmax,
        imax_mppt,
        in_vnom,
        in_vmin,
        in_vmax,
        in_mpp_vmin,
        in_mpp_vmax,
        out_pmax,
        out_imax,
        out_vnom,
        out_freq,
        eficiencia_inv,
        max_thd,
        fator_potencia,
    )

    st.write("🔧 Buscando clima para:", nome_cidade, "-", pais)
    clima = Classes.Clima_Ambiente(nome_cidade, pais, data)

    # ------------------------------------------- Simulando modelo -------------------------------------------
    st.write("⚙️ Iniciando a simulação do modelo...")
    modelo = Agentes.Modelo_Fotovoltaico(painel, nm_paineis, inversor, 1, clima)

    progress_bar = st.progress(0)
    for i in range(Iteracao_Sim):
        modelo.step()
        if i % (Iteracao_Sim // 100) == 0:
            progress_bar.progress(i / Iteracao_Sim)

    st.success("✅ Simulação concluída!")

    # ------------------------------------------- Resultados Painel DC -------------------------------------------
    Model_val = modelo.Valores_Painel_DC.get_model_vars_dataframe()
    Agent_val = modelo.Valores_Painel_DC.get_agent_vars_dataframe()

    P_DC_Out = Model_val.iloc[:, 0].copy()
    V_DC_Out = Model_val.iloc[:, 1].copy()

    agent_Vars = Agent_val.reset_index()
    agent_Vars = agent_Vars[agent_Vars["AgentID"] == 2]
    agent_Vars = agent_Vars[["Step", "Corrente_DC"]]
    I_DC_Out = agent_Vars.iloc[:, 1].copy()

    Time = np.linspace(0, T_sim, len(P_DC_Out))

    st.subheader("📊 Resultados DC - Painel Fotovoltaico")

    fig_dc, axs_dc = plt.subplots(3, 1, figsize=(18, 8))

    axs_dc[0].plot(Time, P_DC_Out, label="Potência DC")
    axs_dc[0].set_ylabel("Potência [W]")
    axs_dc[0].legend()
    axs_dc[0].grid(True)

    axs_dc[1].plot(Time, V_DC_Out, label="Tensão DC")
    axs_dc[1].set_ylabel("Tensão [V]")
    axs_dc[1].legend()
    axs_dc[1].grid(True)

    axs_dc[2].plot(Time, I_DC_Out, label="Corrente DC")
    axs_dc[2].set_xlabel("Tempo [s]")
    axs_dc[2].set_ylabel("Corrente [A]")
    axs_dc[2].legend()
    axs_dc[2].grid(True)

    plt.tight_layout()
    st.pyplot(fig_dc)

    # ------------------------------------------- Resultados Inversor AC -------------------------------------------
    st.subheader("📊 Resultados AC - Saída do Inversor")

    df = modelo.Valores_Inversor_AC.get_agent_vars_dataframe()
    df = df.reset_index()
    df_agente = df[df["AgentID"] == 20]
    df_agente = df_agente[["Step", "Tensao_AC", "Corrente_AC"]]

    Tensao_Out = df_agente.iloc[:, 1].copy()
    Corrente_Out = df_agente.iloc[:, 2].copy()

    fig_ac, axs_ac = plt.subplots(2, 1, figsize=(18, 6))

    axs_ac[0].plot(Time, Tensao_Out, label="Tensão AC")
    axs_ac[0].set_ylabel("Tensão [V]")
    axs_ac[0].legend()
    axs_ac[0].grid(True)

    axs_ac[1].plot(Time, Corrente_Out, label="Corrente AC")
    axs_ac[1].set_xlabel("Tempo [s]")
    axs_ac[1].set_ylabel("Corrente [A]")
    axs_ac[1].legend()
    axs_ac[1].grid(True)

    plt.tight_layout()
    st.pyplot(fig_ac)

    st.success("🏁 Simulação e plotagens concluídas com sucesso!")
