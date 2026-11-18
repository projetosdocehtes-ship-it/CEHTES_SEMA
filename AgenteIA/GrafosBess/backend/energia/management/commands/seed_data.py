from django.core.management.base import BaseCommand

from energia.models import Componente, Fabricante, Projeto, ProjetoDiagrama, TipoComponente


class Command(BaseCommand):
    help = "Cria dados iniciais do simulador."

    def handle(self, *args, **options):
        tipos = [
            ("modulo_fv", "Módulo FV"),
            ("string_box", "String Box"),
            ("seccionadora_cc", "Seccionadora CC"),
            ("dps_cc", "DPS CC"),
            ("inversor", "Inversor FV"),
            ("barramento", "Barramento BT"),
            ("bateria", "Banco de Baterias"),
            ("pcs", "PCS"),
            ("disjuntor", "Disjuntor"),
            ("transformador", "Transformador"),
            ("protecao_mt", "Proteção MT"),
            ("poc", "Ponto de Conexão"),
            ("carga", "Carga"),
            ("gerador_diesel", "Gerador Diesel"),
            ("clima", "Clima/Ambiente"),
        ]
        for codigo, nome in tipos:
            TipoComponente.objects.get_or_create(codigo=codigo, defaults={"nome": nome})

        sungrow, _ = Fabricante.objects.get_or_create(nome="Sungrow")
        weg, _ = Fabricante.objects.get_or_create(nome="WEG")
        byd, _ = Fabricante.objects.get_or_create(nome="BYD")
        deye, _ = Fabricante.objects.get_or_create(nome="Deye")
        huawei, _ = Fabricante.objects.get_or_create(nome="Huawei")
        cummins, _ = Fabricante.objects.get_or_create(nome="Cummins")
        cliente, _ = Fabricante.objects.get_or_create(nome="Cliente")
        sistema, _ = Fabricante.objects.get_or_create(nome="Sistema")
        generico, _ = Fabricante.objects.get_or_create(nome="Genérico")

        def tipo(codigo):
            return TipoComponente.objects.get(codigo=codigo)

        componentes = [
            dict(fabricante=generico, tipo=tipo("modulo_fv"), nome_modelo="Módulo Mono 550W", potencia_kw=0.55, tensao_nominal_v=41.5, corrente_nominal_a=13.2),
            dict(fabricante=generico, tipo=tipo("modulo_fv"), nome_modelo="CanadianSolar TOPBiHiKu6 610W", potencia_kw=0.61, tensao_nominal_v=40.8, corrente_nominal_a=14.96),
            dict(fabricante=generico, tipo=tipo("string_box"), nome_modelo="String Box 4 Entradas"),
            dict(fabricante=generico, tipo=tipo("seccionadora_cc"), nome_modelo="Seccionadora 1500Vdc", tensao_nominal_v=1500),
            dict(fabricante=generico, tipo=tipo("dps_cc"), nome_modelo="DPS CC Classe II", tensao_nominal_v=1500),
            dict(fabricante=sungrow, tipo=tipo("inversor"), nome_modelo="SG125CX", potencia_kw=125, tensao_nominal_v=800, modo_operacao="grid_following"),
            dict(fabricante=deye, tipo=tipo("inversor"), nome_modelo="SUN-35K-SG01HP3-EU-BM", potencia_kw=38.5, tensao_nominal_v=380, modo_operacao="hibrido"),
            dict(fabricante=huawei, tipo=tipo("inversor"), nome_modelo="SUN2000-100KTL-M2", potencia_kw=100, tensao_nominal_v=380, modo_operacao="grid_following"),
            dict(fabricante=generico, tipo=tipo("barramento"), nome_modelo="Barramento BT 800V", tensao_nominal_v=800),
            dict(fabricante=generico, tipo=tipo("barramento"), nome_modelo="AC - Bus_ac_1 - 380V", tensao_nominal_v=380),
            dict(fabricante=byd, tipo=tipo("bateria"), nome_modelo="Battery Max 500", energia_kwh=500, tensao_nominal_v=1200),
            dict(fabricante=byd, tipo=tipo("bateria"), nome_modelo="Battery-Box Premium HVS", energia_kwh=500, tensao_nominal_v=480),
            dict(fabricante=generico, tipo=tipo("bateria"), nome_modelo="BESS Container 1MWh", energia_kwh=1000, tensao_nominal_v=800),
            dict(fabricante=sungrow, tipo=tipo("pcs"), nome_modelo="PCS 250kW", potencia_kw=250, tensao_nominal_v=800, modo_operacao="bidirecional"),
            dict(fabricante=generico, tipo=tipo("disjuntor"), nome_modelo="Disjuntor BT 800V", tensao_nominal_v=800),
            dict(fabricante=weg, tipo=tipo("transformador"), nome_modelo="Trafo 0,8/34,5kV 1MVA", potencia_kw=1000),
            dict(fabricante=weg, tipo=tipo("protecao_mt"), nome_modelo="Relé 50/51 27/59 32 67"),
            dict(fabricante=generico, tipo=tipo("poc"), nome_modelo="Ponto de Conexão 34,5kV"),
            dict(fabricante=cliente, tipo=tipo("carga"), nome_modelo="Comercial - Mercado", potencia_kw=12000, tensao_nominal_v=380),
            dict(fabricante=cliente, tipo=tipo("carga"), nome_modelo="Escola", potencia_kw=180, tensao_nominal_v=380),
            dict(fabricante=cliente, tipo=tipo("carga"), nome_modelo="Hospital", potencia_kw=450, tensao_nominal_v=380),
            dict(fabricante=cummins, tipo=tipo("gerador_diesel"), nome_modelo="C275D5", potencia_kw=275, tensao_nominal_v=380),
            dict(fabricante=sistema, tipo=tipo("clima"), nome_modelo="Goiania"),
        ]

        for item in componentes:
            Componente.objects.get_or_create(
                fabricante=item["fabricante"],
                tipo=item["tipo"],
                nome_modelo=item["nome_modelo"],
                defaults={
                    "potencia_kw": item.get("potencia_kw"),
                    "tensao_nominal_v": item.get("tensao_nominal_v"),
                    "corrente_nominal_a": item.get("corrente_nominal_a"),
                    "energia_kwh": item.get("energia_kwh"),
                    "modo_operacao": item.get("modo_operacao", ""),
                },
            )

        projeto, _ = Projeto.objects.get_or_create(
            nome="Projeto Exemplo",
            defaults={"descricao": "Projeto inicial do simulador."},
        )
        ProjetoDiagrama.objects.get_or_create(
            projeto=projeto,
            defaults={"layout_json": {"nodes": [], "edges": []}, "simulacao_json": {}},
        )

        self.stdout.write(self.style.SUCCESS("Dados iniciais criados com sucesso."))
