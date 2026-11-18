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
        ]
        for codigo, nome in tipos:
            TipoComponente.objects.get_or_create(codigo=codigo, defaults={"nome": nome})

        sungrow, _ = Fabricante.objects.get_or_create(nome="Sungrow")
        weg, _ = Fabricante.objects.get_or_create(nome="WEG")
        byd, _ = Fabricante.objects.get_or_create(nome="BYD")
        generico, _ = Fabricante.objects.get_or_create(nome="Genérico")

        def tipo(codigo):
            return TipoComponente.objects.get(codigo=codigo)

        componentes = [
            dict(fabricante=generico, tipo=tipo("modulo_fv"), nome_modelo="Módulo Mono 550W", potencia_kw=0.55, tensao_nominal_v=41.5, corrente_nominal_a=13.2),
            dict(fabricante=generico, tipo=tipo("string_box"), nome_modelo="String Box 4 Entradas"),
            dict(fabricante=generico, tipo=tipo("seccionadora_cc"), nome_modelo="Seccionadora 1500Vdc", tensao_nominal_v=1500),
            dict(fabricante=generico, tipo=tipo("dps_cc"), nome_modelo="DPS CC Classe II", tensao_nominal_v=1500),
            dict(fabricante=sungrow, tipo=tipo("inversor"), nome_modelo="SG125CX", potencia_kw=125, tensao_nominal_v=800, modo_operacao="grid_following"),
            dict(fabricante=generico, tipo=tipo("barramento"), nome_modelo="Barramento BT 800V", tensao_nominal_v=800),
            dict(fabricante=byd, tipo=tipo("bateria"), nome_modelo="Battery Max 500", energia_kwh=500, tensao_nominal_v=1200),
            dict(fabricante=sungrow, tipo=tipo("pcs"), nome_modelo="PCS 250kW", potencia_kw=250, tensao_nominal_v=800, modo_operacao="bidirecional"),
            dict(fabricante=generico, tipo=tipo("disjuntor"), nome_modelo="Disjuntor BT 800V", tensao_nominal_v=800),
            dict(fabricante=weg, tipo=tipo("transformador"), nome_modelo="Trafo 0,8/34,5kV 1MVA", potencia_kw=1000),
            dict(fabricante=weg, tipo=tipo("protecao_mt"), nome_modelo="Relé 50/51 27/59 32 67"),
            dict(fabricante=generico, tipo=tipo("poc"), nome_modelo="Ponto de Conexão 34,5kV"),
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
