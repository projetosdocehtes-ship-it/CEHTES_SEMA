from django.db import models


class Lei(models.Model):
    numero: str = models.CharField(max_length=50, unique=True)
    titulo: str = models.CharField(max_length=255)
    texto = models.TextField()
    data_publicacao = models.DateField()
    data_atualizacao = models.DateField(auto_now=True)

    def __str__(self):
        return f"{self.numero} - {self.titulo}"
