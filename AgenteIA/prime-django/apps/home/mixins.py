import datetime
import logging

from django.db import models
from django.http import HttpResponse
from django_tables2.config import RequestConfig
from django_tables2.export.export import TableExport

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")


class PedidoONRMixin(models.Model):
    protocolo_onr: str = models.CharField(max_length=100, blank=True, null=True)
    data_entrada_onr: datetime = models.DateTimeField(blank=True, null=True)
    valor_total_onr = models.DecimalField(
        default=0,
        blank=False,
        decimal_places=2,
        max_digits=10,
        null=True,
    )

    class Meta:
        abstract = True
        verbose_name = "PedidoCertidao ONR"
        verbose_name_plural = "Pedidos ONR"


class ExportExcelMixin:
    export_param = "export"
    table_class = None
    filterset_class = None

    def exportar_table(self, table):
        exporter = TableExport("xlsx", table, exclude_columns=("acoes"))
        response = HttpResponse(
            exporter.export(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = 'attachment; filename="export.xlsx"'
        return response

    def export_data(self, request):
        filterset = self.filterset_class(request.GET, queryset=self.get_queryset())
        table = self.table_class(filterset.qs)
        RequestConfig(request).configure(table)
        return self.exportar_table(table)

    def get(self, request, *args, **kwargs):
        if self.export_param in request.GET:
            return self.export_data(request)
        return super().get(request, *args, **kwargs)
