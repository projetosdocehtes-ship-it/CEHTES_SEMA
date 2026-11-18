import datetime
import uuid

from django.db import models

from apps.home.models import Livro02

# from apps.home.models import Livro03 as Livro03


class UUIDPrimaryKeyField(models.UUIDField):
    def __init__(self, *args, **kwargs) -> None:
        kwargs["primary_key"] = True
        kwargs["default"] = uuid.uuid4
        kwargs["editable"] = False
        super().__init__(*args, **kwargs)

    @staticmethod
    def generate_uuid() -> uuid.UUID:
        return uuid.uuid4()


# Create your models here.
class Pgnm(models.Model):
    id: uuid.uuid4 = UUIDPrimaryKeyField()
    imovel = models.ForeignKey(
        Livro02,
        on_delete=models.CASCADE,
        related_name="imovel_pgnm",
        default=None,
    )
    livro = models.BigIntegerField(db_index=True)
    created_at: datetime = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.id} - {self.imovel} - {self.livro} - {self.created_at}"


class PgnmAuditor(models.Model):
    id: uuid.uuid4 = UUIDPrimaryKeyField()
    livro = models.BigIntegerField()
    created_at: datetime = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.id} - {self.livro} - {self.created_at}"
