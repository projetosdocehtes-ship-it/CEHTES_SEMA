"""
Modulo para consulta de tarifas da ANEEL (Grupo A, modalidades Azul e Verde).
Fonte de dados:
https://dadosabertos.aneel.gov.br/dataset/tarifas-distribuidoras-energia-eletrica/resource/fcf2906c-7c32-4b9b-a637-054e7a5234f4
"""

from __future__ import annotations

from datetime import datetime
import warnings
import requests
import pandas as pd


class TarifasANEEL:
    API_BASE_URL = "https://dadosabertos.aneel.gov.br/api/3/action/datastore_search"
    RESOURCE_ID = "fcf2906c-7c32-4b9b-a637-054e7a5234f4"

    HORARIOS_PONTA = {
        "inicio": 18,
        "fim": 21,
        "dias_semana": [0, 1, 2, 3, 4],
    }

    _cache = {}
    _cache_duracao_segundos = 3600

    def __init__(self, distribuidora="EQUATORIAL GO", usar_api=True, grupo="A4"):
        self.distribuidora_codigo = str(distribuidora).upper().strip()
        self.grupo = grupo
        self.usar_api = usar_api
        self.dados_tarifa = None
        self.fonte_dados = "fallback"

        if usar_api:
            try:
                self._carregar_dados_api()
            except Exception as exc:
                warnings.warn(f"Erro ao buscar API da ANEEL: {exc}. Usando dados fallback.")
                self._usar_dados_fallback()
        else:
            self._usar_dados_fallback()

    @staticmethod
    def _to_float_br(valor):
        if valor is None:
            return 0.0
        texto = str(valor).strip()
        if not texto:
            return 0.0
        texto = texto.replace(".", "").replace(",", ".")
        try:
            return float(texto)
        except Exception:
            return 0.0

    def _buscar_dados_api(self, distribuidora_query, grupo):
        chave = f"{distribuidora_query}|{grupo}"
        agora = datetime.now().timestamp()
        cache_item = self._cache.get(chave)
        if cache_item and (agora - cache_item["ts"]) < self._cache_duracao_segundos:
            return cache_item["df"]

        params = {
            "resource_id": self.RESOURCE_ID,
            "q": distribuidora_query,
            "limit": 100000,
        }
        resp = requests.get(self.API_BASE_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("success"):
            raise RuntimeError(f"Resposta invalida da API: {data}")

        registros = data.get("result", {}).get("records", [])
        if not registros:
            raise RuntimeError(f"Nenhum registro encontrado para '{distribuidora_query}'")

        df = pd.DataFrame(registros)
        if "SigSubGrupo" in df.columns:
            df = df[df["SigSubGrupo"] == grupo]
        elif "DscSubGrupo" in df.columns:
            df = df[df["DscSubGrupo"] == grupo]

        if df.empty:
            raise RuntimeError(f"Nenhum registro para grupo {grupo} em '{distribuidora_query}'")

        self._cache[chave] = {"df": df.copy(), "ts": agora}
        return df

    def _carregar_dados_api(self):
        df = self._buscar_dados_api(self.distribuidora_codigo, self.grupo)

        if "DatInicioVigencia" in df.columns:
            df["DatInicioVigencia_dt"] = pd.to_datetime(df["DatInicioVigencia"], errors="coerce")
            dt_max = df["DatInicioVigencia_dt"].max()
            df = df[df["DatInicioVigencia_dt"] == dt_max].copy()

        if "DscBaseTarifaria" in df.columns:
            df = df[df["DscBaseTarifaria"] == "Tarifa de Aplicação"].copy()

        if df.empty:
            raise RuntimeError("Sem dados de Tarifa de Aplicacao na API")

        self.dados_tarifa = self._extrair_tarifas_api(df)
        self.fonte_dados = "api"

        # Se veio muito incompleto, completa com fallback.
        if self._tarifas_incompletas(self.dados_tarifa):
            dados_api = self.dados_tarifa
            self._usar_dados_fallback()
            dados_fb = self.dados_tarifa

            for mod in ("azul", "verde"):
                for chave, valor in dados_fb[mod].items():
                    if dados_api[mod].get(chave, 0) == 0:
                        dados_api[mod][chave] = valor

            if not dados_api.get("scee"):
                dados_api["scee"] = dados_fb.get("scee", {})

            self.dados_tarifa = dados_api
            self.fonte_dados = "api+fallback"
            warnings.warn("Tarifas da API incompletas. Complementando com fallback.")

        self._normalizar_compatibilidade()

    @staticmethod
    def _tarifas_incompletas(dados):
        verde = dados.get("verde", {})
        azul = dados.get("azul", {})
        s_verde = verde.get("te_ponta", 0) + verde.get("te_fora_ponta", 0) + verde.get("tusd_fora_ponta_consumo", 0)
        s_azul = azul.get("te_ponta", 0) + azul.get("te_fora_ponta", 0) + azul.get("tusd_fora_ponta_consumo", 0)
        return s_verde == 0 or s_azul == 0

    def _extrair_tarifas_api(self, df):
        primeiro = df.iloc[0]
        dados = {
            "nome": str(primeiro.get("SigAgente", self.distribuidora_codigo)),
            "uf": "GO" if "GO" in str(primeiro.get("SigAgente", "")) else "XX",
            "vigencia": str(primeiro.get("DatInicioVigencia", "")),
            "grupo": self.grupo,
            "azul": {
                "tusd_ponta_demanda": 0.0,
                "tusd_fora_ponta_demanda": 0.0,
                "tusd_ponta_consumo": 0.0,
                "tusd_fora_ponta_consumo": 0.0,
                "te_ponta": 0.0,
                "te_fora_ponta": 0.0,
            },
            "verde": {
                "tusd_demanda": 0.0,
                "tusd_ponta_consumo": 0.0,
                "tusd_fora_ponta_consumo": 0.0,
                "te_ponta": 0.0,
                "te_fora_ponta": 0.0,
            },
            "scee": {
                "azul": {"te_ponta": 0.0, "te_fora_ponta": 0.0, "tusd_ponta": 0.0, "tusd_fora_ponta": 0.0},
                "verde": {"te_ponta": 0.0, "te_fora_ponta": 0.0, "tusd_ponta": 0.0, "tusd_fora_ponta": 0.0},
            },
            "tarifa_exportacao": 0.0,
        }

        # SCEE
        df_scee = df[df.get("DscDetalhe", "") == "SCEE"] if "DscDetalhe" in df.columns else pd.DataFrame()
        for modalidade in ("Azul", "Verde"):
            if df_scee.empty:
                break
            mod_key = modalidade.lower()
            dmod = df_scee[df_scee.get("DscModalidadeTarifaria", "") == modalidade]
            if dmod.empty:
                continue

            ponta = dmod[dmod.get("NomPostoTarifario", "") == "Ponta"]
            fora = dmod[dmod.get("NomPostoTarifario", "") == "Fora ponta"]
            if not ponta.empty:
                r = ponta.iloc[0]
                dados["scee"][mod_key]["te_ponta"] = self._to_float_br(r.get("VlrTE", 0)) / 1000
                dados["scee"][mod_key]["tusd_ponta"] = self._to_float_br(r.get("VlrTUSD", 0)) / 1000
            if not fora.empty:
                r = fora.iloc[0]
                dados["scee"][mod_key]["te_fora_ponta"] = self._to_float_br(r.get("VlrTE", 0)) / 1000
                dados["scee"][mod_key]["tusd_fora_ponta"] = self._to_float_br(r.get("VlrTUSD", 0)) / 1000

        # Consumo e demanda
        df_na = df[df.get("DscDetalhe", "") == "Não se aplica"] if "DscDetalhe" in df.columns else df

        for modalidade in ("Azul", "Verde"):
            mod_key = modalidade.lower()
            dmod = df_na[df_na.get("DscModalidadeTarifaria", "") == modalidade] if "DscModalidadeTarifaria" in df_na.columns else df_na
            if dmod.empty:
                continue

            ponta = dmod[dmod.get("NomPostoTarifario", "") == "Ponta"]
            fora = dmod[dmod.get("NomPostoTarifario", "") == "Fora ponta"]
            nao_posto = dmod[dmod.get("NomPostoTarifario", "") == "Não se aplica"]

            # kWh (MWh na base, divide por 1000)
            if not ponta.empty:
                r = ponta.iloc[0]
                te = self._to_float_br(r.get("VlrTE", 0)) / 1000
                tusd = self._to_float_br(r.get("VlrTUSD", 0)) / 1000
                dados[mod_key]["te_ponta"] = te
                dados[mod_key]["tusd_ponta_consumo"] = tusd
            if not fora.empty:
                r = fora.iloc[0]
                te = self._to_float_br(r.get("VlrTE", 0)) / 1000
                tusd = self._to_float_br(r.get("VlrTUSD", 0)) / 1000
                dados[mod_key]["te_fora_ponta"] = te
                dados[mod_key]["tusd_fora_ponta_consumo"] = tusd

            # demanda (kW)
            if modalidade == "Azul":
                ponta_kw = ponta[ponta.get("DscUnidadeTerciaria", "") == "kW"] if not ponta.empty else pd.DataFrame()
                fora_kw = fora[fora.get("DscUnidadeTerciaria", "") == "kW"] if not fora.empty else pd.DataFrame()
                if not ponta_kw.empty:
                    dados["azul"]["tusd_ponta_demanda"] = self._to_float_br(ponta_kw.iloc[0].get("VlrTUSD", 0))
                if not fora_kw.empty:
                    dados["azul"]["tusd_fora_ponta_demanda"] = self._to_float_br(fora_kw.iloc[0].get("VlrTUSD", 0))
            else:
                na_kw = nao_posto[nao_posto.get("DscUnidadeTerciaria", "") == "kW"] if not nao_posto.empty else pd.DataFrame()
                if not na_kw.empty:
                    dados["verde"]["tusd_demanda"] = self._to_float_br(na_kw.iloc[0].get("VlrTUSD", 0))

        # fallback simples de exportacao
        s_verde_ponta = dados["scee"]["verde"]["te_ponta"] + dados["scee"]["verde"]["tusd_ponta"]
        s_azul_ponta = dados["scee"]["azul"]["te_ponta"] + dados["scee"]["azul"]["tusd_ponta"]
        if s_verde_ponta > 0:
            dados["tarifa_exportacao"] = dados["scee"]["verde"]["te_ponta"]
        elif s_azul_ponta > 0:
            dados["tarifa_exportacao"] = dados["scee"]["azul"]["te_ponta"]

        return dados

    def _usar_dados_fallback(self):
        fallback = {
            "EQUATORIAL GO": {
                "nome": "Equatorial Goias",
                "uf": "GO",
                "vigencia": "fallback",
                "grupo": "A4",
                "azul": {
                    "tusd_ponta_demanda": 46.20,
                    "tusd_fora_ponta_demanda": 22.58,
                    "tusd_ponta_consumo": 0.89,
                    "tusd_fora_ponta_consumo": 0.27,
                    "te_ponta": 0.74,
                    "te_fora_ponta": 0.58,
                },
                "verde": {
                    "tusd_demanda": 22.58,
                    "tusd_ponta_consumo": 0.89,
                    "tusd_fora_ponta_consumo": 0.27,
                    "te_ponta": 2.61,
                    "te_fora_ponta": 0.58,
                },
                "scee": {
                    "azul": {"te_ponta": 0.20, "te_fora_ponta": 0.08, "tusd_ponta": 0.10, "tusd_fora_ponta": 0.04},
                    "verde": {"te_ponta": 0.20, "te_fora_ponta": 0.08, "tusd_ponta": 0.10, "tusd_fora_ponta": 0.04},
                },
                "tarifa_exportacao": 0.20,
            },
            "EQUATORIAL GOIAS": None,
            "CEMIG": {
                "nome": "CEMIG",
                "uf": "MG",
                "vigencia": "fallback",
                "grupo": "A4",
                "azul": {
                    "tusd_ponta_demanda": 42.0,
                    "tusd_fora_ponta_demanda": 21.0,
                    "tusd_ponta_consumo": 0.83,
                    "tusd_fora_ponta_consumo": 0.25,
                    "te_ponta": 0.71,
                    "te_fora_ponta": 0.55,
                },
                "verde": {
                    "tusd_demanda": 21.02,
                    "tusd_ponta_consumo": 0.83,
                    "tusd_fora_ponta_consumo": 0.25,
                    "te_ponta": 2.43,
                    "te_fora_ponta": 0.55,
                },
                "scee": {
                    "azul": {"te_ponta": 0.18, "te_fora_ponta": 0.07, "tusd_ponta": 0.09, "tusd_fora_ponta": 0.03},
                    "verde": {"te_ponta": 0.18, "te_fora_ponta": 0.07, "tusd_ponta": 0.09, "tusd_fora_ponta": 0.03},
                },
                "tarifa_exportacao": 0.18,
            },
        }
        fallback["EQUATORIAL GOIAS"] = fallback["EQUATORIAL GO"].copy()

        if self.distribuidora_codigo not in fallback:
            self.distribuidora_codigo = "EQUATORIAL GO"
            warnings.warn("Distribuidora nao encontrada no fallback. Usando EQUATORIAL GO.")

        self.dados_tarifa = fallback[self.distribuidora_codigo]
        self.fonte_dados = "fallback"
        warnings.warn(f"Usando dados fallback para {self.distribuidora_codigo}")
        self._normalizar_compatibilidade()

    def _normalizar_compatibilidade(self):
        # Chaves legadas esperadas por scripts antigos.
        verde = self.dados_tarifa.get("verde", {})
        self.dados_tarifa["te_ponta"] = verde.get("te_ponta", 0)
        self.dados_tarifa["te_fora_ponta"] = verde.get("te_fora_ponta", 0)
        self.dados_tarifa["tusd_ponta"] = verde.get("tusd_ponta_consumo", 0)
        self.dados_tarifa["tusd_fora_ponta"] = verde.get("tusd_fora_ponta_consumo", 0)

    def get_info_distribuidora(self):
        return {
            "nome": self.dados_tarifa.get("nome", self.distribuidora_codigo),
            "uf": self.dados_tarifa.get("uf", "XX"),
            "vigencia": self.dados_tarifa.get("vigencia", ""),
            "grupo": self.dados_tarifa.get("grupo", self.grupo),
            "fonte": self.fonte_dados,
        }

    def get_tarifas_azul(self):
        return self.dados_tarifa["azul"].copy()

    def get_tarifas_verde(self):
        return self.dados_tarifa["verde"].copy()

    @staticmethod
    def is_horario_ponta(hora, dia_semana=None):
        if dia_semana is None:
            dia_semana = 0
        if dia_semana not in TarifasANEEL.HORARIOS_PONTA["dias_semana"]:
            return False
        return TarifasANEEL.HORARIOS_PONTA["inicio"] <= hora < TarifasANEEL.HORARIOS_PONTA["fim"]

    def calcular_custo_energia_azul(self, energia_kwh_ponta, energia_kwh_fora_ponta,
                                    demanda_ponta_kw, demanda_fora_ponta_kw):
        t = self.dados_tarifa["azul"]
        c_tusd_dem_p = demanda_ponta_kw * t["tusd_ponta_demanda"]
        c_tusd_dem_fp = demanda_fora_ponta_kw * t["tusd_fora_ponta_demanda"]
        c_tusd_cons_p = energia_kwh_ponta * t["tusd_ponta_consumo"]
        c_tusd_cons_fp = energia_kwh_fora_ponta * t["tusd_fora_ponta_consumo"]
        c_te_p = energia_kwh_ponta * t["te_ponta"]
        c_te_fp = energia_kwh_fora_ponta * t["te_fora_ponta"]
        total = c_tusd_dem_p + c_tusd_dem_fp + c_tusd_cons_p + c_tusd_cons_fp + c_te_p + c_te_fp
        return {
            "tusd_demanda_ponta": c_tusd_dem_p,
            "tusd_demanda_fora_ponta": c_tusd_dem_fp,
            "tusd_consumo_ponta": c_tusd_cons_p,
            "tusd_consumo_fora_ponta": c_tusd_cons_fp,
            "te_ponta": c_te_p,
            "te_fora_ponta": c_te_fp,
            "custo_total": total,
        }

    def calcular_custo_energia_verde(self, energia_kwh_ponta, energia_kwh_fora_ponta, demanda_max_kw):
        t = self.dados_tarifa["verde"]
        c_tusd_dem = demanda_max_kw * t["tusd_demanda"]
        c_tusd_cons_p = energia_kwh_ponta * t["tusd_ponta_consumo"]
        c_tusd_cons_fp = energia_kwh_fora_ponta * t["tusd_fora_ponta_consumo"]
        c_te_p = energia_kwh_ponta * t["te_ponta"]
        c_te_fp = energia_kwh_fora_ponta * t["te_fora_ponta"]
        total = c_tusd_dem + c_tusd_cons_p + c_tusd_cons_fp + c_te_p + c_te_fp
        return {
            "tusd_demanda": c_tusd_dem,
            "tusd_consumo_ponta": c_tusd_cons_p,
            "tusd_consumo_fora_ponta": c_tusd_cons_fp,
            "te_ponta": c_te_p,
            "te_fora_ponta": c_te_fp,
            "custo_total": total,
            "energia_total_kwh": energia_kwh_ponta + energia_kwh_fora_ponta,
            "custo_medio_kwh": (total / (energia_kwh_ponta + energia_kwh_fora_ponta)) if (energia_kwh_ponta + energia_kwh_fora_ponta) > 0 else 0,
        }

    @classmethod
    def listar_distribuidoras_api(cls, termo=""):
        params = {"resource_id": cls.RESOURCE_ID, "q": termo, "limit": 5000}
        resp = requests.get(cls.API_BASE_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        registros = data.get("result", {}).get("records", [])
        if not registros:
            return []
        agentes = sorted({str(r.get("SigAgente", "")).strip() for r in registros if r.get("SigAgente")})
        return agentes


if __name__ == "__main__":
    t = TarifasANEEL("EQUATORIAL GO", usar_api=True)
    print(t.get_info_distribuidora())
    print(t.get_tarifas_verde())
