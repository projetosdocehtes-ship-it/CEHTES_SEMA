from django.views.generic.list import ListView

from apps.deposito_previo.models import DepositoPrevio


class DepositoPrevioList(ListView):
    model = DepositoPrevio
    template_name = "deposito_previo/deposito_previo_list.html"
