import logging

from django.http import HttpResponse
from django_tables2.export.export import TableExport
from django.contrib.auth.models import User
from django.db import models

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")
class ExportMixin:
    def get(self, request, *args, **kwargs):
        if "export" in request.GET:
            # Assumindo que o FilterSet e o Table da view estão configurados corretamente
            filterset = self.filterset_class(request.GET, queryset=self.get_queryset())
            table = self.table_class(filterset.qs)
            exporter = TableExport("xlsx", table, exclude_columns=("ação"))
            response = HttpResponse(
                exporter.export(),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            response["Content-Disposition"] = 'attachment; filename="exportados.xlsx"'
            return response
        return super().get(request, *args, **kwargs)
