# from apps.home.models import Livro01Protocolo

# # from apps.home.views import *
# from ..helpers import (

#     get_ids_servicos_para_atualizar_status,
#     get_ids_de_tipo_cancelado,
#     get_ids_de_tipo_exigencia,
#     get_ids_tipo_registrado,


# # ATUALIZANDO OS DADOS NO PROTOCOLO DO COLABORADOR ATUAL
# def Atualizar_Colaborador_Atual_Protocolo(protocolo_id, colaborador_id):
#     protocolo_id = str(protocolo_id).split(".")[0]

#     # ATUALIZANDO OS DADOS NO PROTOCOLO
#     try:
#         b = Livro01Protocolo.objects.get(numero_protocolo=213789)

#         b.colaborador = int(colaborador_id)
#         b.save()
#     except Exception:
#         pass


# # Atualizar ultimo status da TABELA PROTOCOLO
# def Atualizar_Status_Protocolo(protocolo_id, tipo_andamento_id, colaborador_id):
#     # Atualizar STATUS DO PROTOCOLO com a data de FINALIZAÇÃO
#     if tipo_andamento_id in get_ids_tipo_registrado():
#         print("Atualizar DATA")
#     else:
#         if tipo_andamento_id in get_ids_de_tipo_cancelado():
#             print("Atualizar DATA")

#     if tipo_andamento_id in get_ids_servicos_para_atualizar_status():
#         print("Atualizar COLABORADOR")
#         # ATUALIZANDO OS DADOS NO PROTOCOLO DO COLABORADOR ATUAL
#         Atualizar_Colaborador_Atual_Protocolo(protocolo_id, colaborador_id)
