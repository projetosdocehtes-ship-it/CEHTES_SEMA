from django.db import models


class Fabricante(models.Model):
    nome = models.CharField(max_length=150, unique=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class TipoComponente(models.Model):
    codigo = models.CharField(max_length=50, unique=True)
    nome = models.CharField(max_length=100)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Componente(models.Model):
    fabricante = models.ForeignKey(Fabricante, on_delete=models.PROTECT, related_name="componentes")
    tipo = models.ForeignKey(TipoComponente, on_delete=models.PROTECT, related_name="componentes")
    nome_modelo = models.CharField(max_length=200)
    descricao = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)

    potencia_kw = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    tensao_nominal_v = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    corrente_nominal_a = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    energia_kwh = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    modo_operacao = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ["tipo__nome", "fabricante__nome", "nome_modelo"]
        constraints = [
            models.UniqueConstraint(
                fields=["fabricante", "tipo", "nome_modelo"],
                name="unique_modelo_por_tipo_e_fabricante",
            )
        ]

    def __str__(self):
        return f"{self.tipo.nome} - {self.fabricante.nome} - {self.nome_modelo}"


class Projeto(models.Model):
    nome = models.CharField(max_length=200)
    descricao = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return self.nome


class ProjetoDiagrama(models.Model):
    projeto = models.OneToOneField(Projeto, on_delete=models.CASCADE, related_name="diagrama")
    layout_json = models.JSONField(default=dict, blank=True)
    simulacao_json = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"Diagrama de {self.projeto.nome}"
