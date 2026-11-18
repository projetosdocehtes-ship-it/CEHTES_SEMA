from django.contrib.contenttypes.models import ContentType
from django.db import models


class ArquivoManager(models.Manager):
    def for_object(self, obj):
        """Retorna uma queryset de arquivos para um objeto específico."""
        content_type = ContentType.objects.get_for_model(obj)
        return (
            super().get_queryset().filter(content_type=content_type, object_id=obj.id)
        )
