# form_helpers.py
import logging

from crispy_forms.bootstrap import FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Column, Div, Field, Layout, Row, Submit

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")


class AtoFormHelper(FormHelper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form_method = "post"
        self.layout = Layout(
            Div(
                Row(
                    Column(
                        Field("tipo_titulo", css_class="form-control"),
                        css_class="col-md-6",
                    ),
                    Column(
                        Field("ato_praticavel", css_class="form-control"),
                        css_class="col-md-6",
                    ),
                ),
                Row(
                    Column(
                        Field("tipo_emolumento", css_class="form-control"),
                        css_class="col-md-6",
                    ),
                    Column(
                        Field("tipo_tributacao", css_class="form-control"),
                        css_class="col-md-4",
                    ),
                    Column(
                        Field("quantidade", css_class="form-control"),
                        css_class="col-md-2",
                    ),
                ),
                Row(
                    Column(
                        Field("valor_avaliacao", css_class="form-control brlinput"),
                        css_class="col-md-6",
                    ),
                    Column(
                        Field("valor_titulo", css_class="form-control brlinput"),
                        css_class="col-md-6",
                    ),
                ),
                Row(
                    Column(
                        Field("imovel_tipo_registro", css_class="form-control"),
                        css_class="col-md-3",
                    ),
                    Column(
                        Field("imovel_numero_registro", css_class="form-control"),
                        css_class="col-md-3",
                    ),
                    Column(
                        Field("imovel_cartorio", css_class="form-control"),
                        css_class="col-md-2",
                    ),
                    Column(
                        Field("tipo_ato", css_class="form-control"),
                        css_class="col-md-2",
                    ),
                    Column(
                        Field("numero_ato", css_class="form-control"),
                        css_class="col-md-2",
                    ),
                ),
                FormActions(
                    Div(Div(css_class="row"), css_class="container"),
                    Div(
                        Div(
                            Div(
                                Div(
                                    Div(
                                        Submit(
                                            "submit",
                                            "Salvar",
                                            css_class="btn btn-sm btn-primary",
                                        ),
                                        Submit(
                                            "save_and_add_another",
                                            "Salvar e Adicionar Outro",
                                            css_class="btn btn-sm btn-outline-info",
                                        ),
                                        Submit(
                                            "save_and_add_complementar",
                                            "Salvar e Adicionar Ato Complementar",
                                            css_class="btn btn-sm btn-success text-dark",
                                        ),
                                        Submit(
                                            "save_and_next",
                                            "Salvar e ir para o próximo ato",
                                            css_class="btn btn-sm btn-outline-success text-dark",
                                        ),
                                        HTML(
                                            """
                                                <a href="{{ url_todos_atos }}" class="btn btn-sm btn-outline-secondary"><i class="icon feather icon-eye"></i>Todos os Atos</a>
                                                <a href="{{ url_retorno }}" class="btn btn-sm btn-outline-secondary"><i class="fas fa-newspaper d-none d-md-inline-block"></i>Pedido/Protocolo</a>
                                            """,
                                        ),
                                        css_class="d-flex justify-content-end",
                                    ),
                                    css_class="container",
                                ),
                                css_class="row",
                            ),
                            css_class="container",
                        ),
                        css_class="row",
                    ),
                ),
            ),
        )
