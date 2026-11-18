import logging

logger = logging.getLogger(__name__)

SIGNALS_IMPORTED = True


# @receiver(post_migrate)
# def create_initial_data(sender, **kwargs):
#     if sender.name == "apps.minutas_atos":
#         print("Criando variáveis padrão para minutas de atos")
#         VariavelMinutaModeloAto = apps.get_model("minutas_atos", "VariavelMinutaModeloAto")

#         try:
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="Interveniente",
#                 variavel="{{ interveniente }}",
#                 descricao_masculino_simples="interveniente",
#                 descricao_masculino_composto="intervenientes",
#                 descricao_feminino_simples="interveniente",
#                 descricao_feminino_composto="intervenientes",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="a",
#                 variavel="{{ a }}",
#                 descricao_masculino_simples="o",
#                 descricao_masculino_composto="os",
#                 descricao_feminino_simples="a",
#                 descricao_feminino_composto="as",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="abre",
#                 variavel="{{ abre }}",
#                 descricao_masculino_simples="abre",
#                 descricao_masculino_composto="abrem",
#                 descricao_feminino_simples="abre",
#                 descricao_feminino_composto="abrem",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="aceita",
#                 variavel="{{ aceita }}",
#                 descricao_masculino_simples="aceita",
#                 descricao_masculino_composto="aceitam",
#                 descricao_feminino_simples="aceita",
#                 descricao_feminino_composto="aceitam",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="aceitar",
#                 variavel="{{ aceitar }}",
#                 descricao_masculino_simples="aceitar",
#                 descricao_masculino_composto="aceitarem",
#                 descricao_feminino_simples="aceitar",
#                 descricao_feminino_composto="aceitarem",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="aceitava",
#                 variavel="{{ aceitava }}",
#                 descricao_masculino_simples="aceitava",
#                 descricao_masculino_composto="aceitavam",
#                 descricao_feminino_simples="aceitava",
#                 descricao_feminino_composto="aceitavam",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="aceitou",
#                 variavel="{{ aceitou }}",
#                 descricao_masculino_simples="aceitou",
#                 descricao_masculino_composto="aceitaram",
#                 descricao_feminino_simples="aceitou",
#                 descricao_feminino_composto="aceitaram",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="acha",
#                 variavel="{{ acha }}",
#                 descricao_masculino_simples="acha",
#                 descricao_masculino_composto="acham",
#                 descricao_feminino_simples="acha",
#                 descricao_feminino_composto="acham",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="acha-se",
#                 variavel="{{ acha_se }}",
#                 descricao_masculino_simples="acha-se",
#                 descricao_masculino_composto="acham-se",
#                 descricao_feminino_simples="acha-se",
#                 descricao_feminino_composto="acham-se",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="adimplentes",
#                 variavel="{{ adimplente }}",
#                 descricao_masculino_simples="adimplente",
#                 descricao_masculino_composto="adimplentes",
#                 descricao_feminino_simples="adimplente",
#                 descricao_feminino_composto="adimplentes",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="adquirente",
#                 variavel="{{ adquirente }}",
#                 descricao_masculino_simples="adquirente",
#                 descricao_masculino_composto="adquirentes",
#                 descricao_feminino_simples="adquirente",
#                 descricao_feminino_composto="adquirentes",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="adquirir",
#                 variavel="{{ adquirir }}",
#                 descricao_masculino_simples="adquirir",
#                 descricao_masculino_composto="adquiram",
#                 descricao_feminino_simples="adquirir",
#                 descricao_feminino_composto="adquiram",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="alfabetizado",
#                 variavel="{{ alfabetizado }}",
#                 descricao_masculino_simples="alfabetizado",
#                 descricao_masculino_composto="alfabetizados",
#                 descricao_feminino_simples="alfabetizado",
#                 descricao_feminino_composto="alfabetizadas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="aliena",
#                 variavel="{{ aliena }}",
#                 descricao_masculino_simples="aliena",
#                 descricao_masculino_composto="alienam",
#                 descricao_feminino_simples="aliena",
#                 descricao_feminino_composto="alienam",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="aludido",
#                 variavel="{{ aludido }}",
#                 descricao_masculino_simples="aludido",
#                 descricao_masculino_composto="aludidos",
#                 descricao_feminino_simples="aludida",
#                 descricao_feminino_composto="aludidas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="anexado",
#                 variavel="{{ anexado }}",
#                 descricao_masculino_simples="anexado",
#                 descricao_masculino_composto="anexados",
#                 descricao_feminino_simples="anexado",
#                 descricao_feminino_composto="anexados",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="anuente",
#                 variavel="{{ anuene }}",
#                 descricao_masculino_simples="anuene",
#                 descricao_masculino_composto="anuenes",
#                 descricao_feminino_simples="anuene",
#                 descricao_feminino_composto="anuenes",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="análoga",
#                 variavel="{{ analoga }}",
#                 descricao_masculino_simples="análoga",
#                 descricao_masculino_composto="análogas",
#                 descricao_feminino_simples="análoga",
#                 descricao_feminino_composto="análogas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="ao",
#                 variavel="{{ ao }}",
#                 descricao_masculino_simples="ao",
#                 descricao_masculino_composto="aos",
#                 descricao_feminino_simples="ao",
#                 descricao_feminino_composto="aos",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="aposta",
#                 variavel="{{ aposta }}",
#                 descricao_masculino_simples="aposta",
#                 descricao_masculino_composto="apostas",
#                 descricao_feminino_simples="aposta",
#                 descricao_feminino_composto="apostas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="apresenta",
#                 variavel="{{ apresenta }}",
#                 descricao_masculino_simples="apresenta",
#                 descricao_masculino_composto="apresentam",
#                 descricao_feminino_simples="apresenta",
#                 descricao_feminino_composto="apresentam",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="aquele",
#                 variavel="{{ aquele }}",
#                 descricao_masculino_simples="aquele",
#                 descricao_masculino_composto="aqueles",
#                 descricao_feminino_simples="aquela",
#                 descricao_feminino_composto="aquelas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="assegurado",
#                 variavel="{{ assegurado }}",
#                 descricao_masculino_simples="assegurado",
#                 descricao_masculino_composto="assegurados",
#                 descricao_feminino_simples="assegurada",
#                 descricao_feminino_composto="asseguradas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="assina",
#                 variavel="{{ assina }}",
#                 descricao_masculino_simples="assina",
#                 descricao_masculino_composto="assinam",
#                 descricao_feminino_simples="assina",
#                 descricao_feminino_composto="assinam",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="assinar",
#                 variavel="{{ assinar }}",
#                 descricao_masculino_simples="assinar",
#                 descricao_masculino_composto="assinarem",
#                 descricao_feminino_simples="assinar",
#                 descricao_feminino_composto="assinarem",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="assinou",
#                 variavel="{{ assinou }}",
#                 descricao_masculino_simples="assinou",
#                 descricao_masculino_composto="assinaram",
#                 descricao_feminino_simples="assinou",
#                 descricao_feminino_composto="assinaram",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="assistente",
#                 variavel="{{ assistente }}",
#                 descricao_masculino_simples="assistente",
#                 descricao_masculino_composto="assistentes",
#                 descricao_feminino_simples="assistente",
#                 descricao_feminino_composto="assistentes",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="assistido",
#                 variavel="{{ assistido }}",
#                 descricao_masculino_simples="assistido",
#                 descricao_masculino_composto="assistidos",
#                 descricao_feminino_simples="assistida",
#                 descricao_feminino_composto="assistidas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="autor",
#                 variavel="{{ autor }}",
#                 descricao_masculino_simples="autor",
#                 descricao_masculino_composto="autores",
#                 descricao_feminino_simples="autora",
#                 descricao_feminino_composto="autoras",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="autoriza",
#                 variavel="{{ autoriza }}",
#                 descricao_masculino_simples="autoriza",
#                 descricao_masculino_composto="autorizam",
#                 descricao_feminino_simples="autoriza",
#                 descricao_feminino_composto="autorizam",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="autorizado",
#                 variavel="{{ autorizado }}",
#                 descricao_masculino_simples="autorizado",
#                 descricao_masculino_composto="autorizados",
#                 descricao_feminino_simples="autorizada",
#                 descricao_feminino_composto="autorizadas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="avaliado",
#                 variavel="{{ avaliado }}",
#                 descricao_masculino_simples="avaliado",
#                 descricao_masculino_composto="avaliados",
#                 descricao_feminino_simples="avaliada",
#                 descricao_feminino_composto="avaliadas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="ação",
#                 variavel="{{ acao }}",
#                 descricao_masculino_simples="ação",
#                 descricao_masculino_composto="ações",
#                 descricao_feminino_simples="ação",
#                 descricao_feminino_composto="ações",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="bastante",
#                 variavel="{{ bastante }}",
#                 descricao_masculino_simples="bastante",
#                 descricao_masculino_composto="bastantes",
#                 descricao_feminino_simples="bastante",
#                 descricao_feminino_composto="bastantes",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="bem",
#                 variavel="{{ bem }}",
#                 descricao_masculino_simples="bem",
#                 descricao_masculino_composto="bens",
#                 descricao_feminino_simples="bem",
#                 descricao_feminino_composto="bens",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="cadastrado",
#                 variavel="{{ cadastrado }}",
#                 descricao_masculino_simples="cadastrado",
#                 descricao_masculino_composto="cadastrados",
#                 descricao_feminino_simples="cadastrada",
#                 descricao_feminino_composto="cadastradas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="caracterizado",
#                 variavel="{{ caracterizado }}",
#                 descricao_masculino_simples="caracterizado",
#                 descricao_masculino_composto="caracterizados",
#                 descricao_feminino_simples="caracterizada",
#                 descricao_feminino_composto="caracterizadas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="casado",
#                 variavel="{{ casado }}",
#                 descricao_masculino_simples="casado",
#                 descricao_masculino_composto="casados",
#                 descricao_feminino_simples="casada",
#                 descricao_feminino_composto="casadas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="cede",
#                 variavel="{{ cede }}",
#                 descricao_masculino_simples="cede",
#                 descricao_masculino_composto="cedem",
#                 descricao_feminino_simples="cede",
#                 descricao_feminino_composto="cedem",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="cedente",
#                 variavel="{{ cedentes }}",
#                 descricao_masculino_simples="cedente",
#                 descricao_masculino_composto="cedentes",
#                 descricao_feminino_simples="cedente",
#                 descricao_feminino_composto="cedentes",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="cedido",
#                 variavel="{{ cedido }}",
#                 descricao_masculino_simples="cedido",
#                 descricao_masculino_composto="cedidos",
#                 descricao_feminino_simples="cedida",
#                 descricao_feminino_composto="cedidas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="cessionário",
#                 variavel="{{ cessionario }}",
#                 descricao_masculino_simples="cessionário",
#                 descricao_masculino_composto="cessionários",
#                 descricao_feminino_simples="cessionária",
#                 descricao_feminino_composto="cessionárias",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="chamado",
#                 variavel="{{ chamado }}",
#                 descricao_masculino_simples="chamado",
#                 descricao_masculino_composto="chamados",
#                 descricao_feminino_simples="chamada",
#                 descricao_feminino_composto="chamadas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="companheiro",
#                 variavel="{{ companheiro }}",
#                 descricao_masculino_simples="companheiro",
#                 descricao_masculino_composto="companheiros",
#                 descricao_feminino_simples="companheira",
#                 descricao_feminino_composto="companheiras",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="comparecente",
#                 variavel="{{ comparecente }}",
#                 descricao_masculino_simples="comparecente",
#                 descricao_masculino_composto="comparecentes",
#                 descricao_feminino_simples="comparecente",
#                 descricao_feminino_composto="comparecentes",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="compareceu",
#                 variavel="{{ compareceu }}",
#                 descricao_masculino_simples="compareceu",
#                 descricao_masculino_composto="compareceram",
#                 descricao_feminino_simples="compareceu",
#                 descricao_feminino_composto="compareceram",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="comprador",
#                 variavel="{{ comprador }}",
#                 descricao_masculino_simples="comprador",
#                 descricao_masculino_composto="compradores",
#                 descricao_feminino_simples="compradora",
#                 descricao_feminino_composto="compradaras",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="compromete",
#                 variavel="{{ compromete }}",
#                 descricao_masculino_simples="compromete",
#                 descricao_masculino_composto="comprometem",
#                 descricao_feminino_simples="compromete",
#                 descricao_feminino_composto="comprometem",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="comprovante",
#                 variavel="{{ comprovante }}",
#                 descricao_masculino_simples="comprovante",
#                 descricao_masculino_composto="comprovantes",
#                 descricao_feminino_simples="comprovante",
#                 descricao_feminino_composto="comprovantes",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="concede",
#                 variavel="{{ concede }}",
#                 descricao_masculino_simples="concede",
#                 descricao_masculino_composto="concedem",
#                 descricao_feminino_simples="concede",
#                 descricao_feminino_composto="concedem",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="concessionário",
#                 variavel="{{ concessionario }}",
#                 descricao_masculino_simples="concessionário",
#                 descricao_masculino_composto="concessionários",
#                 descricao_feminino_simples="concessionária",
#                 descricao_feminino_composto="concessionárias",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="concessor",
#                 variavel="{{ concessor }}",
#                 descricao_masculino_simples="concessor",
#                 descricao_masculino_composto="concessores",
#                 descricao_feminino_simples="concessora",
#                 descricao_feminino_composto="concessoras",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="concluir",
#                 variavel="{{ concluir }}",
#                 descricao_masculino_simples="concluir",
#                 descricao_masculino_composto="concluirem",
#                 descricao_feminino_simples="concluir",
#                 descricao_feminino_composto="concluirem",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="condômino",
#                 variavel="{{ condomino }}",
#                 descricao_masculino_simples="condômino",
#                 descricao_masculino_composto="condôminos",
#                 descricao_feminino_simples="condômina",
#                 descricao_feminino_composto="condôminas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="confere",
#                 variavel="{{ confere }}",
#                 descricao_masculino_simples="confere",
#                 descricao_masculino_composto="conferem",
#                 descricao_feminino_simples="confere",
#                 descricao_feminino_composto="conferem",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="confessa",
#                 variavel="{{ confessa }}",
#                 descricao_masculino_simples="confessa",
#                 descricao_masculino_composto="confessam",
#                 descricao_feminino_simples="confessa",
#                 descricao_feminino_composto="confessam",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="conferido",
#                 variavel="{{ conferido }}",
#                 descricao_masculino_simples="conferido",
#                 descricao_masculino_composto="conferidos",
#                 descricao_feminino_simples="conferida",
#                 descricao_feminino_composto="conferidas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="confitente",
#                 variavel="{{ confitente }}",
#                 descricao_masculino_simples="confitente",
#                 descricao_masculino_composto="confitentes",
#                 descricao_feminino_simples="confitenta",
#                 descricao_feminino_composto="confitentas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="conhecida",
#                 variavel="{{ conhecido }}",
#                 descricao_masculino_simples="conhecido",
#                 descricao_masculino_composto="conhecidos",
#                 descricao_feminino_simples="conhecida",
#                 descricao_feminino_composto="conhecidas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="constante",
#                 variavel="{{ constante }}",
#                 descricao_masculino_simples="constante",
#                 descricao_masculino_composto="constantes",
#                 descricao_feminino_simples="constante",
#                 descricao_feminino_composto="constantes",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="constitui",
#                 variavel="{{ constitue }}",
#                 descricao_masculino_simples="constitue",
#                 descricao_masculino_composto="constituem",
#                 descricao_feminino_simples="constitue",
#                 descricao_feminino_composto="constituem",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="conta",
#                 variavel="{{ conta }}",
#                 descricao_masculino_simples="conta",
#                 descricao_masculino_composto="contam",
#                 descricao_feminino_simples="conta",
#                 descricao_feminino_composto="contam",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="contou",
#                 variavel="{{ contou }}",
#                 descricao_masculino_simples="contou",
#                 descricao_masculino_composto="contaram",
#                 descricao_feminino_simples="contou",
#                 descricao_feminino_composto="contaram",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="contratado",
#                 variavel="{{ contratado }}",
#                 descricao_masculino_simples="contratado",
#                 descricao_masculino_composto="contratados",
#                 descricao_feminino_simples="contratada",
#                 descricao_feminino_composto="contratadas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="contratante",
#                 variavel="{{ contratante }}",
#                 descricao_masculino_simples="contratante",
#                 descricao_masculino_composto="contratantes",
#                 descricao_feminino_simples="contratante",
#                 descricao_feminino_composto="contratantes",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="contribuinte",
#                 variavel="{{ contribuinte }}",
#                 descricao_masculino_simples="contribuinte",
#                 descricao_masculino_composto="contribuintes",
#                 descricao_feminino_simples="contribuinte",
#                 descricao_feminino_composto="contribuintes",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="contruído",
#                 variavel="{{ contruido }}",
#                 descricao_masculino_simples="contruído",
#                 descricao_masculino_composto="contruídos",
#                 descricao_feminino_simples="contruído",
#                 descricao_feminino_composto="contruídos",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="convencionar",
#                 variavel="{{ convencionar }}",
#                 descricao_masculino_simples="convencionar",
#                 descricao_masculino_composto="convencionarem",
#                 descricao_feminino_simples="convencionar",
#                 descricao_feminino_composto="convencionarem",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="creditado",
#                 variavel="{{ creditado }}",
#                 descricao_masculino_simples="creditado",
#                 descricao_masculino_composto="creditados",
#                 descricao_feminino_simples="creditada",
#                 descricao_feminino_composto="creditadas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="credor",
#                 variavel="{{ credor }}",
#                 descricao_masculino_simples="credor",
#                 descricao_masculino_composto="credores",
#                 descricao_feminino_simples="credora",
#                 descricao_feminino_composto="credoras",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="cujo",
#                 variavel="{{ cujo }}",
#                 descricao_masculino_simples="cujo",
#                 descricao_masculino_composto="cujos",
#                 descricao_feminino_simples="cujo",
#                 descricao_feminino_composto="cujos",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="curador",
#                 variavel="{{ curador }}",
#                 descricao_masculino_simples="curador",
#                 descricao_masculino_composto="curadores",
#                 descricao_feminino_simples="curadora",
#                 descricao_feminino_composto="curadoras",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="dar",
#                 variavel="{{ dar }}",
#                 descricao_masculino_simples="dar",
#                 descricao_masculino_composto="darem",
#                 descricao_feminino_simples="dar",
#                 descricao_feminino_composto="darem",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="de",
#                 variavel="{{ de }}",
#                 descricao_masculino_simples="de",
#                 descricao_masculino_composto="dos",
#                 descricao_feminino_simples="de",
#                 descricao_feminino_composto="dos",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="declara",
#                 variavel="{{ declara }}",
#                 descricao_masculino_simples="declara",
#                 descricao_masculino_composto="declaram",
#                 descricao_feminino_simples="declara",
#                 descricao_feminino_composto="declaram",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="declarado",
#                 variavel="{{ declarado }}",
#                 descricao_masculino_simples="declarado",
#                 descricao_masculino_composto="declarados",
#                 descricao_feminino_simples="declarada",
#                 descricao_feminino_composto="declaradas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="declarante",
#                 variavel="{{ declarante }}",
#                 descricao_masculino_simples="declarante",
#                 descricao_masculino_composto="declarantes",
#                 descricao_feminino_simples="declarante",
#                 descricao_feminino_composto="declarantes",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="declarar",
#                 variavel="{{ declarar }}",
#                 descricao_masculino_simples="declarar",
#                 descricao_masculino_composto="declararem",
#                 descricao_feminino_simples="declarar",
#                 descricao_feminino_composto="declararem",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="declarou",
#                 variavel="{{ declarou }}",
#                 descricao_masculino_simples="declarou",
#                 descricao_masculino_composto="declararam",
#                 descricao_feminino_simples="declarou",
#                 descricao_feminino_composto="declararam",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="defendê-lo",
#                 variavel="{{ defende_lo }}",
#                 descricao_masculino_simples="defendê-lo",
#                 descricao_masculino_composto="defendê-los",
#                 descricao_feminino_simples="defendê-la",
#                 descricao_feminino_composto="defendê-las",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="deixar",
#                 variavel="{{ deixar }}",
#                 descricao_masculino_simples="deixar",
#                 descricao_masculino_composto="deixarem",
#                 descricao_feminino_simples="deixar",
#                 descricao_feminino_composto="deixarem",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="deixou",
#                 variavel="{{ deixou }}",
#                 descricao_masculino_simples="deixou",
#                 descricao_masculino_composto="deixaram",
#                 descricao_feminino_simples="deixou",
#                 descricao_feminino_composto="deixaram",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="demais",
#                 variavel="{{ demais }}",
#                 descricao_masculino_simples="demais",
#                 descricao_masculino_composto="demais",
#                 descricao_feminino_simples="demais",
#                 descricao_feminino_composto="demais",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="denominado",
#                 variavel="{{ denominado }}",
#                 descricao_masculino_simples="denominado",
#                 descricao_masculino_composto="denominados",
#                 descricao_feminino_simples="denominada",
#                 descricao_feminino_composto="denominadas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="dependente",
#                 variavel="{{ dependente }}",
#                 descricao_masculino_simples="dependente",
#                 descricao_masculino_composto="dependentes",
#                 descricao_feminino_simples="dependente",
#                 descricao_feminino_composto="dependentes",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="desaparecido",
#                 variavel="{{ desaparecido }}",
#                 descricao_masculino_simples="desaparecido",
#                 descricao_masculino_composto="desaparecidos",
#                 descricao_feminino_simples="desaparecida",
#                 descricao_feminino_composto="desaparecidas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="deixa",
#                 variavel="{{ deixa }}",
#                 descricao_masculino_simples="deixa",
#                 descricao_masculino_composto="deixam",
#                 descricao_feminino_simples="deixa",
#                 descricao_feminino_composto="deixam",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="dele",
#                 variavel="{{ dele }}",
#                 descricao_masculino_simples="dele",
#                 descricao_masculino_composto="deles",
#                 descricao_feminino_simples="dela",
#                 descricao_feminino_composto="deles",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="descrito",
#                 variavel="{{ descrito }}",
#                 descricao_masculino_simples="descrito",
#                 descricao_masculino_composto="descritos",
#                 descricao_feminino_simples="descrita",
#                 descricao_feminino_composto="descritas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="descrito",
#                 variavel="{{ descrito }}",
#                 descricao_masculino_simples="descrito",
#                 descricao_masculino_composto="descritos",
#                 descricao_feminino_simples="descrita",
#                 descricao_feminino_composto="descritas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="desde",
#                 variavel="{{ desde }}",
#                 descricao_masculino_simples="desde",
#                 descricao_masculino_composto="desde",
#                 descricao_feminino_simples="desde",
#                 descricao_feminino_composto="desde",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="desembargador",
#                 variavel="{{ desembargador }}",
#                 descricao_masculino_simples="desembargador",
#                 descricao_masculino_composto="desembargadores",
#                 descricao_feminino_simples="desembargadora",
#                 descricao_feminino_composto="desembargadoras",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="desembargadora",
#                 variavel="{{ desembargadora }}",
#                 descricao_masculino_simples="desembargador",
#                 descricao_masculino_composto="desembargadores",
#                 descricao_feminino_simples="desembargadora",
#                 descricao_feminino_composto="desembargadoras",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="desembargadores",
#                 variavel="{{ desembargadores }}",
#                 descricao_masculino_simples="desembargador",
#                 descricao_masculino_composto="desembargadores",
#                 descricao_feminino_simples="desembargadora",
#                 descricao_feminino_composto="desembargadoras",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="desembargadoras",
#                 variavel="{{ desembargadoras }}",
#                 descricao_masculino_simples="desembargador",
#                 descricao_masculino_composto="desembargadores",
#                 descricao_feminino_simples="desembargadora",
#                 descricao_feminino_composto="desembargadoras",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="desembaraçado",
#                 variavel="{{ desembaracado }}",
#                 descricao_masculino_simples="desembaraçado",
#                 descricao_masculino_composto="desembaraçados",
#                 descricao_feminino_simples="desembaraçada",
#                 descricao_feminino_composto="desembaraçadas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="desembaraçador",
#                 variavel="{{ desembaracador }}",
#                 descricao_masculino_simples="desembaraçador",
#                 descricao_masculino_composto="desembaraçadores",
#                 descricao_feminino_simples="desembaraçadora",
#                 descricao_feminino_composto="desembaraçadoras",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="desembaraçadora",
#                 variavel="{{ desembaracadora }}",
#                 descricao_masculino_simples="desembaraçador",
#                 descricao_masculino_composto="desembaraçadores",
#                 descricao_feminino_simples="desembaraçadora",
#                 descricao_feminino_composto="desembaraçadoras",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="desembaraçadores",
#                 variavel="{{ desembaracadores }}",
#                 descricao_masculino_simples="desembaraçador",
#                 descricao_masculino_composto="desembaraçadores",
#                 descricao_feminino_simples="desembaraçadora",
#                 descricao_feminino_composto="desembaraçadoras",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="designado",
#                 variavel="{{ designado }}",
#                 descricao_masculino_simples="designado",
#                 descricao_masculino_composto="designados",
#                 descricao_feminino_simples="designada",
#                 descricao_feminino_composto="designadas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="desistente",
#                 variavel="{{ desistente }}",
#                 descricao_masculino_simples="desistente",
#                 descricao_masculino_composto="desistentes",
#                 descricao_feminino_simples="desistente",
#                 descricao_feminino_composto="desistentes",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="desistente usufrutuário",
#                 variavel="{{ desistente_usufrutuario }}",
#                 descricao_masculino_simples="desistente usufrutuário",
#                 descricao_masculino_composto="desistente usufrutuários",
#                 descricao_feminino_simples="desistente usufrutuária",
#                 descricao_feminino_composto="desistente usufrutuárias",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="desonerado",
#                 variavel="{{ desonerado }}",
#                 descricao_masculino_simples="desonerado",
#                 descricao_masculino_composto="desonerados",
#                 descricao_feminino_simples="desonerada",
#                 descricao_feminino_composto="desoneradas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="detentor",
#                 variavel="{{ detentor }}",
#                 descricao_masculino_simples="detentor",
#                 descricao_masculino_composto="detentores",
#                 descricao_feminino_simples="detentora",
#                 descricao_feminino_composto="detentoras",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="devedor",
#                 variavel="{{ devedor }}",
#                 descricao_masculino_simples="devedor",
#                 descricao_masculino_composto="devedores",
#                 descricao_feminino_simples="devedora",
#                 descricao_feminino_composto="devedoras",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="direito",
#                 variavel="{{ direito }}",
#                 descricao_masculino_simples="direito",
#                 descricao_masculino_composto="direitos",
#                 descricao_feminino_simples="direito",
#                 descricao_feminino_composto="direitos",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="dispensado",
#                 variavel="{{ dispensado }}",
#                 descricao_masculino_simples="dispensado",
#                 descricao_masculino_composto="dispensados",
#                 descricao_feminino_simples="dispensada",
#                 descricao_feminino_composto="dispensadas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="disponha",
#                 variavel="{{ disponha }}",
#                 descricao_masculino_simples="disponha",
#                 descricao_masculino_composto="disponham",
#                 descricao_feminino_simples="disponha",
#                 descricao_feminino_composto="disponham",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="disse",
#                 variavel="{{ disse }}",
#                 descricao_masculino_simples="disse",
#                 descricao_masculino_composto="disseram",
#                 descricao_feminino_simples="disse",
#                 descricao_feminino_composto="disseram",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="dito",
#                 variavel="{{ dito }}",
#                 descricao_masculino_simples="dito",
#                 descricao_masculino_composto="ditos",
#                 descricao_feminino_simples="dita",
#                 descricao_feminino_composto="ditas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="do",
#                 variavel="{{ do }}",
#                 descricao_masculino_simples="do",
#                 descricao_masculino_composto="dos",
#                 descricao_feminino_simples="da",
#                 descricao_feminino_composto="ddas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="doador",
#                 variavel="{{ doador }}",
#                 descricao_masculino_simples="doador",
#                 descricao_masculino_composto="doadores",
#                 descricao_feminino_simples="doadora",
#                 descricao_feminino_composto="doadoras",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="domiciliado",
#                 variavel="{{ domiciliado }}",
#                 descricao_masculino_simples="domiciliado",
#                 descricao_masculino_composto="domiciliados",
#                 descricao_feminino_simples="domiciliada",
#                 descricao_feminino_composto="domiciliadas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="domínio",
#                 variavel="{{ dominio }}",
#                 descricao_masculino_simples="domínio",
#                 descricao_masculino_composto="domínios",
#                 descricao_feminino_simples="domínio",
#                 descricao_feminino_composto="domínios",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="donatário",
#                 variavel="{{ donatario }}",
#                 descricao_masculino_simples="donatário",
#                 descricao_masculino_composto="donatários",
#                 descricao_feminino_simples="donatária",
#                 descricao_feminino_composto="donatárias",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="dá",
#                 variavel="{{ da }}",
#                 descricao_masculino_simples="dá",
#                 descricao_masculino_composto="dão",
#                 descricao_feminino_simples="dá",
#                 descricao_feminino_composto="dão",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="e",
#                 variavel="{{ ee }}",
#                 descricao_masculino_simples="e",
#                 descricao_masculino_composto="es",
#                 descricao_feminino_simples="e",
#                 descricao_feminino_composto="es",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="ele",
#                 variavel="{{ ele }}",
#                 descricao_masculino_simples="ele",
#                 descricao_masculino_composto="eles",
#                 descricao_feminino_simples="ela",
#                 descricao_feminino_composto="elas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="emancipa-los",
#                 variavel="{{ emancipa_lo }}",
#                 descricao_masculino_simples="emancipa-lo",
#                 descricao_masculino_composto="emancipa-los",
#                 descricao_feminino_simples="emancipa-la",
#                 descricao_feminino_composto="emancipa-las",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="emancipado",
#                 variavel="{{ emancipado }}",
#                 descricao_masculino_simples="emancipado",
#                 descricao_masculino_composto="emancipados",
#                 descricao_feminino_simples="emancipada",
#                 descricao_feminino_composto="emancipadas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="encontra-se",
#                 variavel="{{ encontra_se }}",
#                 descricao_masculino_simples="encontra-se",
#                 descricao_masculino_composto="encontram-se",
#                 descricao_feminino_simples="encontra-se",
#                 descricao_feminino_composto="encontram-se",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="envolva",
#                 variavel="{{ envolva }}",
#                 descricao_masculino_simples="envolva",
#                 descricao_masculino_composto="envolvam",
#                 descricao_feminino_simples="envolva",
#                 descricao_feminino_composto="envolvam",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="esposo",
#                 variavel="{{ esposo }}",
#                 descricao_masculino_simples="esposo",
#                 descricao_masculino_composto="esposo",
#                 descricao_feminino_simples="esposa",
#                 descricao_feminino_composto="esposa",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="este",
#                 variavel="{{ este }}",
#                 descricao_masculino_simples="este",
#                 descricao_masculino_composto="estes",
#                 descricao_feminino_simples="esta",
#                 descricao_feminino_composto="estas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="estiverem",
#                 variavel="{{ estiver }}",
#                 descricao_masculino_simples="estiver",
#                 descricao_masculino_composto="estiverem",
#                 descricao_feminino_simples="estiver",
#                 descricao_feminino_composto="estiverem",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="está",
#                 variavel="{{ esta }}",
#                 descricao_masculino_simples="está",
#                 descricao_masculino_composto="estão",
#                 descricao_feminino_simples="está",
#                 descricao_feminino_composto="estão",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="exercia",
#                 variavel="{{ exercia }}",
#                 descricao_masculino_simples="exercia",
#                 descricao_masculino_composto="exerciam",
#                 descricao_feminino_simples="exercia",
#                 descricao_feminino_composto="exerciam",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="faz",
#                 variavel="{{ faz }}",
#                 descricao_masculino_simples="faz",
#                 descricao_masculino_composto="fazem",
#                 descricao_feminino_simples="faz",
#                 descricao_feminino_composto="fazem",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="fazer",
#                 variavel="{{ fazer }}",
#                 descricao_masculino_simples="fazer",
#                 descricao_masculino_composto="fazerem",
#                 descricao_feminino_simples="fazer",
#                 descricao_feminino_composto="fazerem",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="fez",
#                 variavel="{{ fez }}",
#                 descricao_masculino_simples="fez",
#                 descricao_masculino_composto="fizeram",
#                 descricao_feminino_simples="fez",
#                 descricao_feminino_composto="fizeram",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="fiador",
#                 variavel="{{ fiador }}",
#                 descricao_masculino_simples="fiador",
#                 descricao_masculino_composto="fiadores",
#                 descricao_feminino_simples="fiadora",
#                 descricao_feminino_composto="fiadoras",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="fica",
#                 variavel="{{ fica }}",
#                 descricao_masculino_simples="fica",
#                 descricao_masculino_composto="ficam",
#                 descricao_feminino_simples="fica",
#                 descricao_feminino_composto="ficam",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="fiduciante",
#                 variavel="{{ fiduciante }}",
#                 descricao_masculino_simples="fiduciante",
#                 descricao_masculino_composto="fiduciantes",
#                 descricao_feminino_simples="fiduciante",
#                 descricao_feminino_composto="fiduciantes",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="fiduciário",
#                 variavel="{{ fiduciario }}",
#                 descricao_masculino_simples="fiduciário",
#                 descricao_masculino_composto="fiduciários",
#                 descricao_feminino_simples="fiduciária",
#                 descricao_feminino_composto="fiduciárias",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="filho",
#                 variavel="{{ filho }}",
#                 descricao_masculino_simples="filho",
#                 descricao_masculino_composto="filhos",
#                 descricao_feminino_simples="filha",
#                 descricao_feminino_composto="filhas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="fique",
#                 variavel="{{ fique }}",
#                 descricao_masculino_simples="fique",
#                 descricao_masculino_composto="fiquem",
#                 descricao_feminino_simples="fique",
#                 descricao_feminino_composto="fiquem",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="fl",
#                 variavel="{{ fl }}",
#                 descricao_masculino_simples="fl.",
#                 descricao_masculino_composto="fls.",
#                 descricao_feminino_simples="fl.",
#                 descricao_feminino_composto="fls.",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="foi",
#                 variavel="{{ foi }}",
#                 descricao_masculino_simples="foi",
#                 descricao_masculino_composto="foram",
#                 descricao_feminino_simples="foi",
#                 descricao_feminino_composto="foram",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="garantidor",
#                 variavel="{{ garantidor }}",
#                 descricao_masculino_simples="garantidor",
#                 descricao_masculino_composto="garantidores",
#                 descricao_feminino_simples="garantidora",
#                 descricao_feminino_composto="garantidoras",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="gozar",
#                 variavel="{{ gozar }}",
#                 descricao_masculino_simples="gozar",
#                 descricao_masculino_composto="gozarem",
#                 descricao_feminino_simples="gozar",
#                 descricao_feminino_composto="gozarem",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="goze",
#                 variavel="{{ goze }}",
#                 descricao_masculino_simples="goze",
#                 descricao_masculino_composto="gozem",
#                 descricao_feminino_simples="goze",
#                 descricao_feminino_composto="gozem",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="habilita",
#                 variavel="{{ habilita }}",
#                 descricao_masculino_simples="habilita",
#                 descricao_masculino_composto="habilitam",
#                 descricao_feminino_simples="habilita",
#                 descricao_feminino_composto="habilitam",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="habilitado",
#                 variavel="{{ habilitado }}",
#                 descricao_masculino_simples="habilitado",
#                 descricao_masculino_composto="habilitados",
#                 descricao_feminino_simples="habilitada",
#                 descricao_feminino_composto="habilitadas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="haver",
#                 variavel="{{ haver }}",
#                 descricao_masculino_simples="haver",
#                 descricao_masculino_composto="havem",
#                 descricao_feminino_simples="haver",
#                 descricao_feminino_composto="havem",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="havido",
#                 variavel="{{ havido }}",
#                 descricao_masculino_simples="havido",
#                 descricao_masculino_composto="havidos",
#                 descricao_feminino_simples="havida",
#                 descricao_feminino_composto="havidas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="herdeiro",
#                 variavel="{{ herdeiro }}",
#                 descricao_masculino_simples="herdeiro",
#                 descricao_masculino_composto="herdeiros",
#                 descricao_feminino_simples="herdeira",
#                 descricao_feminino_composto="herdeiras",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="hipotecário",
#                 variavel="{{ hipotecario }}",
#                 descricao_masculino_simples="hipotecário",
#                 descricao_masculino_composto="hipotecários",
#                 descricao_feminino_simples="hipotecária",
#                 descricao_feminino_composto="hipotecárias",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="identificada",
#                 variavel="{{ identificada }}",
#                 descricao_masculino_simples="identificada",
#                 descricao_masculino_composto="identificadas",
#                 descricao_feminino_simples="identificada",
#                 descricao_feminino_composto="identificadas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="identificado",
#                 variavel="{{ identificado }}",
#                 descricao_masculino_simples="identificado",
#                 descricao_masculino_composto="identificados",
#                 descricao_feminino_simples="identificada",
#                 descricao_feminino_composto="identificadas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="imóvel",
#                 variavel="{{ imovel }}",
#                 descricao_masculino_simples="imóvel",
#                 descricao_masculino_composto="imóveis",
#                 descricao_feminino_simples="imóvel",
#                 descricao_feminino_composto="imóveis",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="indicada",
#                 variavel="{{ indicada }}",
#                 descricao_masculino_simples="indicada",
#                 descricao_masculino_composto="indicadas",
#                 descricao_feminino_simples="indicada",
#                 descricao_feminino_composto="indicadas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="inscrito",
#                 variavel="{{ inscrito }}",
#                 descricao_masculino_simples="inscrito",
#                 descricao_masculino_composto="inscritos",
#                 descricao_feminino_simples="inscrita",
#                 descricao_feminino_composto="inscritas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="justo",
#                 variavel="{{ justo }}",
#                 descricao_masculino_simples="justo",
#                 descricao_masculino_composto="justos",
#                 descricao_feminino_simples="justa",
#                 descricao_feminino_composto="justas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="lavrada",
#                 variavel="{{ lavrado }}",
#                 descricao_masculino_simples="lavrado",
#                 descricao_masculino_composto="lavrados",
#                 descricao_feminino_simples="lavrada",
#                 descricao_feminino_composto="lavradas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="legítimo",
#                 variavel="{{ legitimo }}",
#                 descricao_masculino_simples="legítimo",
#                 descricao_masculino_composto="legítimos",
#                 descricao_feminino_simples="legítima",
#                 descricao_feminino_composto="legítimas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="inscrito_casado",
#                 variavel="{{ inscrito_casado }}",
#                 descricao_masculino_simples="inscrito",
#                 descricao_masculino_composto="inscrito",
#                 descricao_feminino_simples="inscrita",
#                 descricao_feminino_composto="inscrita",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="inscrita_casada",
#                 variavel="{{ inscrita_casada }}",
#                 descricao_masculino_simples="inscrita",
#                 descricao_masculino_composto="inscrita",
#                 descricao_feminino_simples="inscrito",
#                 descricao_feminino_composto="inscrito",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="lhe",
#                 variavel="{{ lhe }}",
#                 descricao_masculino_simples="lhe",
#                 descricao_masculino_composto="lhes",
#                 descricao_feminino_simples="lhe",
#                 descricao_feminino_composto="lhes",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="livre",
#                 variavel="{{ livre }}",
#                 descricao_masculino_simples="livre",
#                 descricao_masculino_composto="livres",
#                 descricao_feminino_simples="livre",
#                 descricao_feminino_composto="livres",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="lo",
#                 variavel="{{ lo }}",
#                 descricao_masculino_simples="lo",
#                 descricao_masculino_composto="los",
#                 descricao_feminino_simples="la",
#                 descricao_feminino_composto="las",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="matriculado",
#                 variavel="{{ matriculado }}",
#                 descricao_masculino_simples="matriculado",
#                 descricao_masculino_composto="matriculados",
#                 descricao_feminino_simples="matriculada",
#                 descricao_feminino_composto="matriculadas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="mesmo",
#                 variavel="{{ mesmo }}",
#                 descricao_masculino_simples="mesmo",
#                 descricao_masculino_composto="mesmos",
#                 descricao_feminino_simples="mesma",
#                 descricao_feminino_composto="mesmas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="meu",
#                 variavel="{{ meu }}",
#                 descricao_masculino_simples="meu",
#                 descricao_masculino_composto="meus",
#                 descricao_feminino_simples="minha",
#                 descricao_feminino_composto="minhas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="na",
#                 variavel="{{ na }}",
#                 descricao_masculino_simples="na",
#                 descricao_masculino_composto="nas",
#                 descricao_feminino_simples="na",
#                 descricao_feminino_composto="na",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="nascido",
#                 variavel="{{ nascido }}",
#                 descricao_masculino_simples="nascido",
#                 descricao_masculino_composto="nascidos",
#                 descricao_feminino_simples="nascida",
#                 descricao_feminino_composto="nascidas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="no",
#                 variavel="{{ no }}",
#                 descricao_masculino_simples="no",
#                 descricao_masculino_composto="nos",
#                 descricao_feminino_simples="no",
#                 descricao_feminino_composto="nos",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="nome",
#                 variavel="{{ nome }}",
#                 descricao_masculino_simples="nome",
#                 descricao_masculino_composto="nomes",
#                 descricao_feminino_simples="nome",
#                 descricao_feminino_composto="nomes",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="nomeado",
#                 variavel="{{ nomeiado }}",
#                 descricao_masculino_simples="nomeiado",
#                 descricao_masculino_composto="nomeiados",
#                 descricao_feminino_simples="nomeiada",
#                 descricao_feminino_composto="nomeiadas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="nomeia",
#                 variavel="{{ nomeia }}",
#                 descricao_masculino_simples="nomeia",
#                 descricao_masculino_composto="nomeiam",
#                 descricao_feminino_simples="nomeia",
#                 descricao_feminino_composto="nomeiam",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="número",
#                 variavel="{{ numero }}",
#                 descricao_masculino_simples="número",
#                 descricao_masculino_composto="números",
#                 descricao_feminino_simples="número",
#                 descricao_feminino_composto="números",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="objeto",
#                 variavel="{{ objeto }}",
#                 descricao_masculino_simples="objeto",
#                 descricao_masculino_composto="objetos",
#                 descricao_feminino_simples="objeto",
#                 descricao_feminino_composto="objetos",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="obriga",
#                 variavel="{{ obriga }}",
#                 descricao_masculino_simples="obriga",
#                 descricao_masculino_composto="obrigam",
#                 descricao_feminino_simples="obriga",
#                 descricao_feminino_composto="obrigam",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="obrigatório",
#                 variavel="{{ obrigatorio }}",
#                 descricao_masculino_simples="obrigatório",
#                 descricao_masculino_composto="obrigatórios",
#                 descricao_feminino_simples="obrigatória",
#                 descricao_feminino_composto="obrigatórias",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="outorga",
#                 variavel="{{ outorga }}",
#                 descricao_masculino_simples="outorga",
#                 descricao_masculino_composto="outorgaram",
#                 descricao_feminino_simples="outorga",
#                 descricao_feminino_composto="outorgaram",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="outorgado",
#                 variavel="{{ outorgado }}",
#                 descricao_masculino_simples="outorgado",
#                 descricao_masculino_composto="outorgados",
#                 descricao_feminino_simples="outorgada",
#                 descricao_feminino_composto="outorgadas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="outorgante",
#                 variavel="{{ outorgante }}",
#                 descricao_masculino_simples="outorgante",
#                 descricao_masculino_composto="outorgantes",
#                 descricao_feminino_simples="outorgante",
#                 descricao_feminino_composto="outorgantes",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="outorgar",
#                 variavel="{{ outorgar }}",
#                 descricao_masculino_simples="outorgar",
#                 descricao_masculino_composto="outorgarem",
#                 descricao_feminino_simples="outorgar",
#                 descricao_feminino_composto="outorgarem",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="outorgou",
#                 variavel="{{ outorgou }}",
#                 descricao_masculino_simples="outorgou",
#                 descricao_masculino_composto="outorgaram",
#                 descricao_feminino_simples="outorgou",
#                 descricao_feminino_composto="outorgaram",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="pagamento",
#                 variavel="{{ pagamento }}",
#                 descricao_masculino_simples="pagamento",
#                 descricao_masculino_composto="pagamentos",
#                 descricao_feminino_simples="pagamento",
#                 descricao_feminino_composto="pagamentos",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="pagar",
#                 variavel="{{ pagar }}",
#                 descricao_masculino_simples="pagar",
#                 descricao_masculino_composto="pagarem",
#                 descricao_feminino_simples="pagar",
#                 descricao_feminino_composto="pagarem",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="pago",
#                 variavel="{{ pago }}",
#                 descricao_masculino_simples="pago",
#                 descricao_masculino_composto="pagos",
#                 descricao_feminino_simples="paga",
#                 descricao_feminino_composto="pagas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="parte",
#                 variavel="{{ parte }}",
#                 descricao_masculino_simples="parte",
#                 descricao_masculino_composto="partes",
#                 descricao_feminino_simples="parte",
#                 descricao_feminino_composto="partes",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="passar",
#                 variavel="{{ passar }}",
#                 descricao_masculino_simples="passar",
#                 descricao_masculino_composto="passarem",
#                 descricao_feminino_simples="passar",
#                 descricao_feminino_composto="passarem",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="pediu",
#                 variavel="{{ pediu }}",
#                 descricao_masculino_simples="pediu",
#                 descricao_masculino_composto="pediram",
#                 descricao_feminino_simples="pediu",
#                 descricao_feminino_composto="pediram",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="pelo",
#                 variavel="{{ pelo }}",
#                 descricao_masculino_simples="pelo",
#                 descricao_masculino_composto="pelos",
#                 descricao_feminino_simples="pela",
#                 descricao_feminino_composto="pelas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="permutante",
#                 variavel="{{ permutante }}",
#                 descricao_masculino_simples="permutante",
#                 descricao_masculino_composto="permutantes",
#                 descricao_feminino_simples="permutante",
#                 descricao_feminino_composto="permutantes",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="pessoa",
#                 variavel="{{ pessoa }}",
#                 descricao_masculino_simples="pessoa",
#                 descricao_masculino_composto="pessoas",
#                 descricao_feminino_simples="pessoa",
#                 descricao_feminino_composto="pessoas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="poderá",
#                 variavel="{{ podera }}",
#                 descricao_masculino_simples="poderá",
#                 descricao_masculino_composto="poderam",
#                 descricao_feminino_simples="poderá",
#                 descricao_feminino_composto="poderam",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="por",
#                 variavel="{{ por }}",
#                 descricao_masculino_simples="por",
#                 descricao_masculino_composto="pelos",
#                 descricao_feminino_simples="pela",
#                 descricao_feminino_composto="pelas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="portador",
#                 variavel="{{ portador }}",
#                 descricao_masculino_simples="portador",
#                 descricao_masculino_composto="portador",
#                 descricao_feminino_simples="portadora",
#                 descricao_feminino_composto="portadora",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="possa",
#                 variavel="{{ possa }}",
#                 descricao_masculino_simples="possa",
#                 descricao_masculino_composto="possam",
#                 descricao_feminino_simples="possa",
#                 descricao_feminino_composto="possam",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="posse",
#                 variavel="{{ posse }}",
#                 descricao_masculino_simples="posse",
#                 descricao_masculino_composto="posses",
#                 descricao_feminino_simples="posse",
#                 descricao_feminino_composto="posses",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="possui",
#                 variavel="{{ possue }}",
#                 descricao_masculino_simples="possue",
#                 descricao_masculino_composto="possuem",
#                 descricao_feminino_simples="possue",
#                 descricao_feminino_composto="possuem",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="possuídor",
#                 variavel="{{ possuidor }}",
#                 descricao_masculino_simples="possuídor",
#                 descricao_masculino_composto="possuídores",
#                 descricao_feminino_simples="possuídora",
#                 descricao_feminino_composto="possuídoras",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="praticar",
#                 variavel="{{ praticar }}",
#                 descricao_masculino_simples="praticar",
#                 descricao_masculino_composto="praticarem",
#                 descricao_feminino_simples="praticar",
#                 descricao_feminino_composto="praticarem",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="presente",
#                 variavel="{{ presente }}",
#                 descricao_masculino_simples="presente",
#                 descricao_masculino_composto="presentes",
#                 descricao_feminino_simples="presente",
#                 descricao_feminino_composto="presentes",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="prestar",
#                 variavel="{{ prestar }}",
#                 descricao_masculino_simples="prestar",
#                 descricao_masculino_composto="prestarem",
#                 descricao_feminino_simples="prestar",
#                 descricao_feminino_composto="prestarem",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="primeiro",
#                 variavel="{{ primeiro }}",
#                 descricao_masculino_simples="primeiro",
#                 descricao_masculino_composto="primeiros",
#                 descricao_feminino_simples="primeira",
#                 descricao_feminino_composto="primeiras",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="procurador",
#                 variavel="{{ procurador }}",
#                 descricao_masculino_simples="procurador",
#                 descricao_masculino_composto="procuradores",
#                 descricao_feminino_simples="procuradora",
#                 descricao_feminino_composto="procuradoras",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="proprietário",
#                 variavel="{{ proprietario }}",
#                 descricao_masculino_simples="proprietário",
#                 descricao_masculino_composto="proprietários",
#                 descricao_feminino_simples="proprietária",
#                 descricao_feminino_composto="proprietárias",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="próprio",
#                 variavel="{{ proprio }}",
#                 descricao_masculino_simples="próprio",
#                 descricao_masculino_composto="próprios",
#                 descricao_feminino_simples="própria",
#                 descricao_feminino_composto="próprias",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="qual",
#                 variavel="{{ qual }}",
#                 descricao_masculino_simples="qual",
#                 descricao_masculino_composto="quis",
#                 descricao_feminino_simples="qual",
#                 descricao_feminino_composto="quis",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="qualificado",
#                 variavel="{{ qualificado }}",
#                 descricao_masculino_simples="qualificado",
#                 descricao_masculino_composto="qualificados",
#                 descricao_feminino_simples="qualificada",
#                 descricao_feminino_composto="qualificadas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="receber",
#                 variavel="{{ receber }}",
#                 descricao_masculino_simples="receber",
#                 descricao_masculino_composto="receberem",
#                 descricao_feminino_simples="receber",
#                 descricao_feminino_composto="receberem",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="recebeu",
#                 variavel="{{ recebeu }}",
#                 descricao_masculino_simples="recebeu",
#                 descricao_masculino_composto="receberam",
#                 descricao_feminino_simples="recebeu",
#                 descricao_feminino_composto="receberam",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="recebido",
#                 variavel="{{ recebido }}",
#                 descricao_masculino_simples="recebido",
#                 descricao_masculino_composto="recebidos",
#                 descricao_feminino_simples="recebido",
#                 descricao_feminino_composto="recebidos",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="recolhido",
#                 variavel="{{ recolhido }}",
#                 descricao_masculino_simples="recolhido",
#                 descricao_masculino_composto="recolhidos",
#                 descricao_feminino_simples="recolhido",
#                 descricao_feminino_composto="recolhidos",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="reconhecido",
#                 variavel="{{ reconhecido }}",
#                 descricao_masculino_simples="reconhecido",
#                 descricao_masculino_composto="reconhecidos",
#                 descricao_feminino_simples="reconhecida",
#                 descricao_feminino_composto="reconhecidas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="reconher",
#                 variavel="{{ reconhe }}",
#                 descricao_masculino_simples="reconhe",
#                 descricao_masculino_composto="reconhem",
#                 descricao_feminino_simples="reconhe",
#                 descricao_feminino_composto="reconhem",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="recorrer",
#                 variavel="{{ recorre }}",
#                 descricao_masculino_simples="recorre",
#                 descricao_masculino_composto="recorrem",
#                 descricao_feminino_simples="recorre",
#                 descricao_feminino_composto="recorrem",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="referido",
#                 variavel="{{ referido }}",
#                 descricao_masculino_simples="referido",
#                 descricao_masculino_composto="referidos",
#                 descricao_feminino_simples="referida",
#                 descricao_feminino_composto="referidas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="registrado",
#                 variavel="{{ registrado }}",
#                 descricao_masculino_simples="registrado",
#                 descricao_masculino_composto="registrados",
#                 descricao_feminino_simples="registrada",
#                 descricao_feminino_composto="registradas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="renunciado",
#                 variavel="{{ renunciado }}",
#                 descricao_masculino_simples="renunciado",
#                 descricao_masculino_composto="renunciados",
#                 descricao_feminino_simples="renunciado",
#                 descricao_feminino_composto="renunciados",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="renunciante",
#                 variavel="{{ renuciante }}",
#                 descricao_masculino_simples="renuciante",
#                 descricao_masculino_composto="renuciantes",
#                 descricao_feminino_simples="renuciante",
#                 descricao_feminino_composto="renuciantes",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="renunciar",
#                 variavel="{{ renunciar }}",
#                 descricao_masculino_simples="renunciar",
#                 descricao_masculino_composto="renunciarem",
#                 descricao_feminino_simples="renunciar",
#                 descricao_feminino_composto="renunciarem",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="repetir",
#                 variavel="{{ repetir }}",
#                 descricao_masculino_simples="repetir",
#                 descricao_masculino_composto="repetirem",
#                 descricao_feminino_simples="repetir",
#                 descricao_feminino_composto="repetirem",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="representado",
#                 variavel="{{ representado }}",
#                 descricao_masculino_simples="representado",
#                 descricao_masculino_composto="representados",
#                 descricao_feminino_simples="representada",
#                 descricao_feminino_composto="representadas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="representante",
#                 variavel="{{ representante }}",
#                 descricao_masculino_simples="representante",
#                 descricao_masculino_composto="representantes",
#                 descricao_feminino_simples="representante",
#                 descricao_feminino_composto="representantes",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="representar",
#                 variavel="{{ representa }}",
#                 descricao_masculino_simples="representa",
#                 descricao_masculino_composto="representa-los",
#                 descricao_feminino_simples="representa",
#                 descricao_feminino_composto="representa-las",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="representá-lo",
#                 variavel="{{ representa_lo }}",
#                 descricao_masculino_simples="representá-lo",
#                 descricao_masculino_composto="representá-los",
#                 descricao_feminino_simples="representá-la",
#                 descricao_feminino_composto="representá-las",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="requerer",
#                 variavel="{{ requerer }}",
#                 descricao_masculino_simples="requerer",
#                 descricao_masculino_composto="requererem",
#                 descricao_feminino_simples="requerer",
#                 descricao_feminino_composto="requererem",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="reserva",
#                 variavel="{{ reserva }}",
#                 descricao_masculino_simples="reserva",
#                 descricao_masculino_composto="reservam",
#                 descricao_feminino_simples="reserva",
#                 descricao_feminino_composto="reservam",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="residente",
#                 variavel="{{ residente }}",
#                 descricao_masculino_simples="residente",
#                 descricao_masculino_composto="residentes",
#                 descricao_feminino_simples="residente",
#                 descricao_feminino_composto="residentes",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="resolve",
#                 variavel="{{ resolve }}",
#                 descricao_masculino_simples="resolve",
#                 descricao_masculino_composto="resolvem",
#                 descricao_feminino_simples="resolve",
#                 descricao_feminino_composto="resolvem",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="resolveu",
#                 variavel="{{ resolveu }}",
#                 descricao_masculino_simples="resolveu",
#                 descricao_masculino_composto="resolveram",
#                 descricao_feminino_simples="resolveu",
#                 descricao_feminino_composto="resolveram",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="responder",
#                 variavel="{{ responder }}",
#                 descricao_masculino_simples="responder",
#                 descricao_masculino_composto="responderem",
#                 descricao_feminino_simples="responder",
#                 descricao_feminino_composto="responderem",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="retificar",
#                 variavel="{{ retificar }}",
#                 descricao_masculino_simples="retificar",
#                 descricao_masculino_composto="retificarem",
#                 descricao_feminino_simples="retificar",
#                 descricao_feminino_composto="retificarem",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="satisfeito",
#                 variavel="{{ satisfeito }}",
#                 descricao_masculino_simples="satisfeito",
#                 descricao_masculino_composto="satisfeitos",
#                 descricao_feminino_simples="satisfeita",
#                 descricao_feminino_composto="satisfeitas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="seguinte",
#                 variavel="{{ seguinte }}",
#                 descricao_masculino_simples="seguinte",
#                 descricao_masculino_composto="seguintes",
#                 descricao_feminino_simples="seguinte",
#                 descricao_feminino_composto="seguintes",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="segundo",
#                 variavel="{{ segundo }}",
#                 descricao_masculino_simples="segundo",
#                 descricao_masculino_composto="segundos",
#                 descricao_feminino_simples="segunda",
#                 descricao_feminino_composto="segundas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="senhor",
#                 variavel="{{ senhor }}",
#                 descricao_masculino_simples="senhor",
#                 descricao_masculino_composto="senhores",
#                 descricao_feminino_simples="senhora",
#                 descricao_feminino_composto="senhoras",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="ser",
#                 variavel="{{ ser }}",
#                 descricao_masculino_simples="ser",
#                 descricao_masculino_composto="serem",
#                 descricao_feminino_simples="see",
#                 descricao_feminino_composto="serem",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="servidão",
#                 variavel="{{ servidao }}",
#                 descricao_masculino_simples="servidão",
#                 descricao_masculino_composto="servidões",
#                 descricao_feminino_simples="servidão",
#                 descricao_feminino_composto="servidões",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="será",
#                 variavel="{{ sera }}",
#                 descricao_masculino_simples="será",
#                 descricao_masculino_composto="serão",
#                 descricao_feminino_simples="será",
#                 descricao_feminino_composto="serão",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="seu",
#                 variavel="{{ seu }}",
#                 descricao_masculino_simples="seu",
#                 descricao_masculino_composto="seus",
#                 descricao_feminino_simples="sua",
#                 descricao_feminino_composto="suas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="solteiro",
#                 variavel="{{ solteiro }}",
#                 descricao_masculino_simples="solteiro",
#                 descricao_masculino_composto="solteiros",
#                 descricao_feminino_simples="solteira",
#                 descricao_feminino_composto="solteiras",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="substabelece",
#                 variavel="{{ substabelece }}",
#                 descricao_masculino_simples="substabelece",
#                 descricao_masculino_composto="substabelecem",
#                 descricao_feminino_simples="substabelece",
#                 descricao_feminino_composto="substabelecem",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="sócio",
#                 variavel="{{ socio }}",
#                 descricao_masculino_simples="sócio",
#                 descricao_masculino_composto="sócios",
#                 descricao_feminino_simples="sócia",
#                 descricao_feminino_composto="sócias",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="tem",
#                 variavel="{{ tem }}",
#                 descricao_masculino_simples="tem",
#                 descricao_masculino_composto="têm",
#                 descricao_feminino_simples="tem",
#                 descricao_feminino_composto="têm",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="tem-no",
#                 variavel="{{ tem_no }}",
#                 descricao_masculino_simples="tem-no",
#                 descricao_masculino_composto="tem-nos",
#                 descricao_feminino_simples="tem-no",
#                 descricao_feminino_composto="tem-nos",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="ter",
#                 variavel="{{ ter }}",
#                 descricao_masculino_simples="ter",
#                 descricao_masculino_composto="terem",
#                 descricao_feminino_simples="ter",
#                 descricao_feminino_composto="terem",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="terem",
#                 variavel="{{ terem }}",
#                 descricao_masculino_simples="ter",
#                 descricao_masculino_composto="terem",
#                 descricao_feminino_simples="ter",
#                 descricao_feminino_composto="terem",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="tinha",
#                 variavel="{{ tinha }}",
#                 descricao_masculino_simples="tinha",
#                 descricao_masculino_composto="tinham",
#                 descricao_feminino_simples="tinha",
#                 descricao_feminino_composto="tinham",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="todo",
#                 variavel="{{ todo }}",
#                 descricao_masculino_simples="todo",
#                 descricao_masculino_composto="todos",
#                 descricao_feminino_simples="toda",
#                 descricao_feminino_composto="todas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="transfere",
#                 variavel="{{ transfere }}",
#                 descricao_masculino_simples="transfere",
#                 descricao_masculino_composto="transferem",
#                 descricao_feminino_simples="transfere",
#                 descricao_feminino_composto="transferem",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="transmite",
#                 variavel="{{ transmite }}",
#                 descricao_masculino_simples="transmite",
#                 descricao_masculino_composto="transmitem",
#                 descricao_feminino_simples="transmite",
#                 descricao_feminino_composto="transmitem",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="transmitente",
#                 variavel="{{ transmitente }}",
#                 descricao_masculino_simples="transmitente",
#                 descricao_masculino_composto="transmitentes",
#                 descricao_feminino_simples="transmitentes",
#                 descricao_feminino_composto="transmitentes",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="transmitir",
#                 variavel="{{ transmitir }}",
#                 descricao_masculino_simples="transmitir",
#                 descricao_masculino_composto="transmitirem",
#                 descricao_feminino_simples="transmitir",
#                 descricao_feminino_composto="transmitirem",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="tutor",
#                 variavel="{{ tutor }}",
#                 descricao_masculino_simples="tutor",
#                 descricao_masculino_composto="tutores",
#                 descricao_feminino_simples="tutora",
#                 descricao_feminino_composto="tutoras",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="usar",
#                 variavel="{{ usar }}",
#                 descricao_masculino_simples="usar",
#                 descricao_masculino_composto="usarem",
#                 descricao_feminino_simples="usar",
#                 descricao_feminino_composto="usarem",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="use",
#                 variavel="{{ use }}",
#                 descricao_masculino_simples="use",
#                 descricao_masculino_composto="usem",
#                 descricao_feminino_simples="use",
#                 descricao_feminino_composto="usem",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="usufrutuário",
#                 variavel="{{ usufrutuario }}",
#                 descricao_masculino_simples="usufrutuário",
#                 descricao_masculino_composto="usufrutuários",
#                 descricao_feminino_simples="usufrutuária",
#                 descricao_feminino_composto="usufrutuárias",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="vem",
#                 variavel="{{ vem }}",
#                 descricao_masculino_simples="vem",
#                 descricao_masculino_composto="vêm",
#                 descricao_feminino_simples="vem",
#                 descricao_feminino_composto="vêm",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="vende",
#                 variavel="{{ vende }}",
#                 descricao_masculino_simples="vende",
#                 descricao_masculino_composto="vendem",
#                 descricao_feminino_simples="vende",
#                 descricao_feminino_composto="vendem",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="vende-lo",
#                 variavel="{{ vende_lo }}",
#                 descricao_masculino_simples="vende-lo",
#                 descricao_masculino_composto="vende-los",
#                 descricao_feminino_simples="vende-la",
#                 descricao_feminino_composto="vende-las",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="vendedor",
#                 variavel="{{ vendedor }}",
#                 descricao_masculino_simples="vendedor",
#                 descricao_masculino_composto="vendedores",
#                 descricao_feminino_simples="vendedora",
#                 descricao_feminino_composto="vendedoras",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="vender",
#                 variavel="{{ vender }}",
#                 descricao_masculino_simples="vender",
#                 descricao_masculino_composto="venderem",
#                 descricao_feminino_simples="vender",
#                 descricao_feminino_composto="venderem",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="vendido",
#                 variavel="{{ vendido }}",
#                 descricao_masculino_simples="vendido",
#                 descricao_masculino_composto="vendidos",
#                 descricao_feminino_simples="vendida",
#                 descricao_feminino_composto="vendidas",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="vendê-lo",
#                 variavel="{{ vende-lo }}",
#                 descricao_masculino_simples="vendê-lo",
#                 descricao_masculino_composto="vendê-los",
#                 descricao_feminino_simples="vendê-la",
#                 descricao_feminino_composto="vendê-las",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="verdadeira",
#                 variavel="{{ verdadeira }}",
#                 descricao_masculino_simples="verdadeira",
#                 descricao_masculino_composto="verdadeiras",
#                 descricao_feminino_simples="verdadeira",
#                 descricao_feminino_composto="verdadeiras",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="vier",
#                 variavel="{{ vier }}",
#                 descricao_masculino_simples="vier",
#                 descricao_masculino_composto="vierem",
#                 descricao_feminino_simples="vier",
#                 descricao_feminino_composto="vierem",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="vinha",
#                 variavel="{{ vinha }}",
#                 descricao_masculino_simples="vinha",
#                 descricao_masculino_composto="vinham",
#                 descricao_feminino_simples="vinha",
#                 descricao_feminino_composto="vinham",
#             )
#             VariavelMinutaModeloAto.objects.get_or_create(
#                 descricao="à",
#                 variavel="{{ a_crase }}",
#                 descricao_masculino_simples="à",
#                 descricao_masculino_composto="às",
#                 descricao_feminino_simples="à",
#                 descricao_feminino_composto="às",
#             )

#         except ProgrammingError as e:
#             logger.error(f"ERRO ao acessar a tabela VariavelMinutaModeloAto no banco de dados: ")
