import logging
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework.authtoken.views import obtain_auth_token
from apps.cartorios.views import check_inactivity

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.authentication.urls")),
    path("", include(("apps.home.urls", "home"), namespace="home")),
    path("comum/", include("apps.comum.urls", namespace="comum")),
    path("pedidos/", include("apps.pedidos.urls", namespace="pedidos")),
    path("", include("apps.modelos.urls", namespace="modelos")),
    path("deposito_previo/", include("apps.deposito_previo.urls", namespace="deposito_previo")),
    path("minuta_exigencia/", include("apps.minuta_exigencia.urls", namespace="minuta_exigencia")),
    path("minutas_atos/", include("apps.minutas_atos.urls", namespace="minutas_atos")),
    path("integracoes/", include("apps.integracoes.urls", namespace="integracoes")),
    path("pessoas/", include("apps.pessoas.urls", namespace="pessoas")),
    path("ged/", include("apps.ged.urls", namespace="ged")),
    path("select2/", include("django_select2.urls")),
    path("", include("apps.accounts.urls")),
    path("", include("admin_datta.urls")),
    path("verificar-inatividade/", view=check_inactivity, name="check_inactivity"),
    path("", include("apps.mapeamentos.urls", namespace="mapeamentos")),
    path("senhas", include("apps.senhas.urls", namespace="senhas")),
    path("ckeditor5/", include("django_ckeditor_5.urls"), name="ck_editor_5_upload_file"),
]
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

try:
    urlpatterns.append(path("", include("apps.samples.urls")))
except Exception:
    pass


try:
    urlpatterns.append(path("api/", include("api.urls")))
    urlpatterns.append(path("login/jwt/", view=obtain_auth_token))
except Exception:
    pass


if settings.HABILITAR_DEBUG_TOOLBAR:
    import debug_toolbar

    urlpatterns += [
        path("__debug__/", include(debug_toolbar.urls)),
    ]
