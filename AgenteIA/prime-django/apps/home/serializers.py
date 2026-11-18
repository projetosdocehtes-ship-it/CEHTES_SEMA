from rest_framework import serializers

from apps.home.models import Livro01Protocolo
from apps.home.models.models_certidoes import PedidoCertidaoImovel


class ProtocoloSerializer(serializers.ModelSerializer):
    class Meta:
        model = Livro01Protocolo
        fields = "__all__"


class PedidoCertidaoImovelSerializer(serializers.ModelSerializer):
    class Meta:
        model = PedidoCertidaoImovel
        fields = ["id", "cartorio", "numero_registro", "tipo_registro", "pedido_id"]
