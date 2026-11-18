from apps.Equipamentos.services.json_builder import ProjetoEnergiaBuilder


class ArquivoSimulacaoService:
    @staticmethod
    def criar_arquivo_simulacao(projeto, inversor):
        corrente_falha_maxima = float(str(inversor.corrente_falha_maxima).replace(",", "."))
        fator_de_potencia_fpa = float(str(inversor.fator_de_potencia_fpa).replace(",", "."))
        curva_eficiencia      = float(str(inversor.curva_eficiencia).replace(",", "."))

        builder = (
            ProjetoEnergiaBuilder(
                nome_projeto=projeto.nome_projeto,
                conectado_rede=False,
            )
            .add_config_simulacao()
            .add_falhas_padrao()
            .set_clima(projeto.localidade, projeto.latitude, projeto.longitude)
            .add_painel(
                pv_id="PV_1",
                fabricante_painel="CanadianSolar",
                modelo_painel="TOPBiHiKu6-610W",
                Pmp=610,
                Isc=15.97,
                Voc=48,
                Imp=14.96,
                Vmp=40.8,
                Uisc=0.05,
                Uvoc=-0.25,
                Upmp=-0.29,
                material_painel="Silicio",
                eficiencia=22.6,
                quantidade=[20, 1],
            )
            .add_inversor(
                inv_id="Inv_1",
                fabricante_inversor=inversor.marca,
                modelo_inversor=inversor.modelo,
                Nm_MPPT=inversor.numero_hidrogenio,
                In_Pmax=int(inversor.pot_max_entrada),
                Imax_MPPT=36,
                In_Vnom=int(inversor.tensao_dc_nominal),
                In_Vmin=int(inversor.intervalo_tensao_dc_inicial),
                In_Vmax=int(inversor.intervalo_tensao_dc_final),
                In_MPP_Vmin=int(inversor.intervalo_tensao_dc_inicial),
                In_MPP_Vmax=int(inversor.intervalo_tensao_mppt_final),
                Out_Pmax=38.5,
                Out_Imax=float(corrente_falha_maxima),
                Out_VL_nom=int(inversor.intervalo_tensao_ac_final),
                Out_Freq=int(inversor.frequencia),
                Eficiencia=float(curva_eficiencia),
                Max_THD=int(inversor.distorcoes_harmonicas_totais),
                Fator_pot=float(fator_de_potencia_fpa),
                Nm_fases=3,
                smart=False,
                quantidade=1,
            )
            .add_carga(
                carga_id="Load_1",
                nome_carga="Mercado",
                tipo_carga=projeto.categoria_projeto,
                curva_carga=0,
                s_instalada=12000,
                fp=0.9999,
                v_nom=380,
                f_rede=60,
                quantidade=1,
            )
            .add_barramento(
                bus_id="Bus_ac_1",
                tipo="AC",
                fases=3,
                V_linha_nominal=380,
                V_fase_nominal=220,
                V_min=0.9,
                V_max=1.1,
            )
            .add_conexao("Clima_Ambiente", "PV_1")
            .add_conexao("PV_1", "Inv_1")
            .add_conexao("Batt_1", "Inv_1")
            .add_conexao("Inv_1", "Bus_ac_1")
            .add_conexao("Bus_ac_1", "Load_1")
        )

        data = builder.build()

        projeto.conteudo_json = data
        projeto.salvar_json_no_filefield(data)

        return projeto
