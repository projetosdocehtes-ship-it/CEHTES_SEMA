from django.db import models
from django.urls import reverse

# Create your models here.
# class DiarioAuxiliar(models.Model):
#     DATA_STATUS = (
#         ("pendente", "Pendente"),
#         ("concluido", "Concluído"),
#     )
#     data = models.DateField(verbose_name="Data")
#     descricao = models.TextField(verbose_name="Descrição")
#     responsavel = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Responsável")
#     status:str = models.CharField(
#         max_length=10, choices=DATA_STATUS, default="pendente", verbose_name="Status"
#     )

#     def __str__(self):
#         return f"{self.descricao[:50]}... - {self.status}"

#     def get_absolute_url(self):
#         return reverse("app:diario_auxiliar_detail", kwargs={"pk": self.pk})


class DepositoPrevio(models.Model):
    DEPOSITO_STATUS = (
        ("pendente", "Pendente"),
        ("confirmado", "Confirmado"),
    )
    valor = models.DecimalField(
        blank=False,
        max_digits=10,
        decimal_places=2,
        verbose_name="Valor",
        help_text="Valor do depósito prévio",
    )
    data = models.DateField(verbose_name="Data")
    servico: str = models.CharField(max_length=200, verbose_name="Serviço")
    status: str = models.CharField(
        max_length=10,
        choices=DEPOSITO_STATUS,
        default="pendente",
        verbose_name="Status",
    )
    observacoes = models.TextField(blank=True, verbose_name="Observações")

    # Como o seu objeto será identificado em todo o sistema. Incluindo em listas e lookups.
    def __str__(self) -> str:
        return f"{self.servico} - {self.valor} - {self.status}"

    # Usado pelo Django para diversos relacionamentos automáticos e redirecionamentos
    def get_absolute_url(self):
        return reverse("app:deposito_previo_detail", kwargs={"pk": self.pk})
