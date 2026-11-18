import logging

from django.db import models

logger = logging.getLogger(__name__)

logger.debug(f"Iniciando {__name__}")


class SequencialIDMixin(models.Model):
    id_sequencial = models.IntegerField(unique=True, null=True, blank=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.id_sequencial is None:
            last_id = self.__class__.objects.all().order_by("id_sequencial").last()
            if last_id and last_id.id_sequencial is not None:
                self.id_sequencial = last_id.id_sequencial + 1
            else:
                total = self.__class__.objects.all().count()
                self.id_sequencial = total + 1
        super().save(*args, **kwargs)
