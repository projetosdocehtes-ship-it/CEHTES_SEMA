from haystack import indexes

from apps.home.models import Livro02


class Livro02Index(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    numero = indexes.IntegerField(model_attr="numero", null=True)
    tipo = indexes.CharField(model_attr="tipo", null=True)
    municipio = indexes.CharField(model_attr="municipio", null=True)
    texto = indexes.CharField(model_attr="texto", null=True)

    def get_model(self):
        return Livro02

    def index_queryset(self, using=None):
        """Used when the entire index for model is updated."""
        return self.get_model().objects.all()
