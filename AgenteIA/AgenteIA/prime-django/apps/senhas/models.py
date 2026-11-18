from django.db import models


class Senha(models.Model):
    numero = models.IntegerField(verbose_name="Número da Senha")
    tipo_atendimento = models.CharField(
        max_length=50,
        verbose_name="Tipo de Atendimento",
        help_text="Ex: Atendimento Geral, Prioritário",
    )
    data_hora_criacao = models.DateTimeField(
        auto_now_add=True, verbose_name="Data e Hora de Criação"
    )
    chamada = models.BooleanField(default=False, verbose_name="Senha Chamada")

    def __str__(self):
        return f"{self.tipo_atendimento} - {self.numero}"