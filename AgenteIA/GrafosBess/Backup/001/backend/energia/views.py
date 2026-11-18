from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from .models import Componente, Fabricante, Projeto, ProjetoDiagrama, TipoComponente
from .serializers import (
    ComponenteSerializer,
    FabricanteSerializer,
    ProjetoDiagramaSerializer,
    ProjetoSerializer,
    TipoComponenteSerializer,
)
from .services import simular_diagrama


class FabricanteViewSet(viewsets.ModelViewSet):
    queryset = Fabricante.objects.all()
    serializer_class = FabricanteSerializer


class TipoComponenteViewSet(viewsets.ModelViewSet):
    queryset = TipoComponente.objects.all()
    serializer_class = TipoComponenteSerializer


class ComponenteViewSet(viewsets.ModelViewSet):
    queryset = Componente.objects.select_related("fabricante", "tipo").all()
    serializer_class = ComponenteSerializer


class ProjetoViewSet(viewsets.ModelViewSet):
    queryset = Projeto.objects.all()
    serializer_class = ProjetoSerializer

    @action(detail=True, methods=["get", "post"], url_path="diagrama")
    def diagrama(self, request, pk=None):
        projeto = self.get_object()
        diagrama, _ = ProjetoDiagrama.objects.get_or_create(
            projeto=projeto,
            defaults={"layout_json": {"nodes": [], "edges": []}, "simulacao_json": {}},
        )

        if request.method == "GET":
            return Response(ProjetoDiagramaSerializer(diagrama).data)

        layout_json = request.data.get("layout_json", {"nodes": [], "edges": []})
        simulacao = simular_diagrama(layout_json)

        diagrama.layout_json = layout_json
        diagrama.simulacao_json = simulacao
        diagrama.save(update_fields=["layout_json", "simulacao_json"])

        return Response(ProjetoDiagramaSerializer(diagrama).data, status=status.HTTP_200_OK)


@api_view(["POST"])
def simular_view(request):
    layout_json = request.data.get("layout_json", {"nodes": [], "edges": []})
    return Response(simular_diagrama(layout_json))
