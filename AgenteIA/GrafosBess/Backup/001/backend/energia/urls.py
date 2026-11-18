from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ComponenteViewSet,
    FabricanteViewSet,
    ProjetoViewSet,
    TipoComponenteViewSet,
    simular_view,
)

router = DefaultRouter()
router.register(r"fabricantes", FabricanteViewSet)
router.register(r"tipos", TipoComponenteViewSet)
router.register(r"componentes", ComponenteViewSet)
router.register(r"projetos", ProjetoViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("simular/", simular_view, name="simular_view"),
]
