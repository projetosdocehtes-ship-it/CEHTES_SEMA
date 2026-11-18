from datetime import datetime


class ProjetoEnergiaBuilder:
    def __init__(self, nome_projeto: str, conectado_rede: bool = False):
        self.data = {
            "nome_projeto": nome_projeto,
            "conectado_rede": conectado_rede,
            "Config_Simulacao": [],
            "Falhas_sim": [],
            "Clima_Ambiente": [],
            "painel_info": [],
            "inversor_info": [],
            "cargas_info": [],
            "bateria_info": [],
            "barramento_info": [],
            "geradordiesel_info": [],
            "geradorbiogas_info": [],
            "eletrolizador_info": [],
            "celulahidrogenio_info": [],
            "turbinaeolica_info": [],
            "grafo_conexoes": [],
        }

    def add_config_simulacao(
        self,
        tipo="Transiente",
        passo=2e-5,
        tempo=1,
        algoritmo="RK45",
        tol=1e-8,
    ):
        self.data["Config_Simulacao"].append(
            {
                "Tipo_Sim": tipo,
                "Passo_sim": passo,
                "Tempo_sim": tempo,
                "Algoritmo_EDO": algoritmo,
                "Tol_relativa": tol,
            },
        )
        return self

    def add_falhas_padrao(self):
        self.data["Falhas_sim"] = [
            {
                "Tipo_Falha": "Mudanca_Temperatura",
                "T_falha": [],
                "duracao_falha": [],
                "Val_Temp": [],
            },
            {
                "Tipo_Falha": "Mudanca_Irradiancia",
                "T_falha": [],
                "duracao_falha": [],
                "Val_Irrad": [],
            },
            {
                "Tipo_Falha": "Mudanca_Carga",
                "T_falha": [],
                "duracao_falha": [],
                "Tipo": [],
                "Pot_Carga": [],
            },
            {
                "Tipo_Falha": "Curto_Circuito_CC",
                "T_falha": [],
                "String_falha": [],
                "duracao_falha": [],
            },
            {
                "Tipo_Falha": "Curto_Circuito_CA",
                "T_falha": [],
                "duracao_falha": [],
            },
        ]
        return self

    def set_clima(self, cidade, latitude, longitude, pais="BR", data=None):
        if not data:
            data = int(datetime.now().strftime("%Y%m%d"))

        self.data["Clima_Ambiente"] = [
            {
                "clima_id": "Clima_Ambiente",
                "nome_cidade": cidade,
                "Latitude": latitude,
                "Longitude": longitude,
                "pais": pais,
                "data": data,
            },
        ]
        return self

    def add_painel(self, **kwargs):
        self.data["painel_info"].append(kwargs)
        return self

    def add_inversor(self, **kwargs):
        self.data["inversor_info"].append(kwargs)
        return self

    def add_carga(self, **kwargs):
        self.data["cargas_info"].append(kwargs)
        return self

    def add_bateria(self, **kwargs):
        self.data["bateria_info"].append(kwargs)
        return self

    def add_barramento(self, **kwargs):
        self.data["barramento_info"].append(kwargs)
        return self

    def add_conexao(self, origem, destino):
        self.data["grafo_conexoes"].append({"between": [origem, destino]})
        return self

    def build(self):
        return self.data
