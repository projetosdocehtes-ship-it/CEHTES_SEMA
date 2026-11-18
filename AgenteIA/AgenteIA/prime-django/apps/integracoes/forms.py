# forms.py no aplicativo 'caixa'
# from django import forms

# from apps.home.models import AtoPratica, EstadoCivil

# from .models import MinutaLigacaoAto, MinutaModeloAto


# class EstadoCivilForm(forms.ModelForm):
#     class Meta:
#         model = EstadoCivil
#         fields = ["descricao_estado_civil", "exibir", "observacao"]
#         labels = {
#             "descricao_estado_civil": "Título - Descrição da estado_civil",
#             "exibir": "Exibir para o cliente esta estado_civil? (S/N)",
#             "observacao": "Observação",
#         }
#         widgets = {
#             "descricao_estado_civil": forms.TextInput(attrs={"class": "form-control"}),
#             "exibir": forms.TextInput(attrs={"class": "form-control"}),
#             "observacao": forms.TextInput(
#                 attrs={"class": "form-control", "placeholder": "observacao"}
#             ),
#         }


# class MinutaAtoForm(forms.ModelForm):
#     class Meta:
#         model = MinutaModeloAto
#         fields = ["titulo", "subtitulo", "observacao"]
#         labels = {
#             "titulo": "Título - descrição da minuta",
#             "subtitulo": "SubTítulo",
#             "observacao": "Observação",
#         }
#         widgets = {
#             "titulo": forms.TextInput(attrs={"class": "form-control"}),
#             "subtitulo": forms.TextInput(attrs={"class": "form-control"}),
#             "observacao": forms.TextInput(
#                 attrs={"class": "form-control", "placeholder": "observacao"}
#             ),
#         }


# # Este formulário é usado para vincular a minuta de exigência com o ato.
# class MinutaLigacaoAtoForm(forms.ModelForm):
#     minuta_exigencia = forms.ModelChoiceField(
#         queryset=MinutaModeloAto.objects.all().order_by("titulo"),
#         label="Descrição da Minuta",
#         widget=forms.Select(attrs={"class": "form-control"}),
#         empty_label="Selecione o ato",
#     )

#     ato_id = forms.ModelChoiceField(
#         queryset=AtoPratica.objects.all().order_by("tipo_ato"),
#         label="Descrição do Ato",
#         widget=forms.Select(attrs={"class": "form-control"}),
#         empty_label="Selecione o ato a vinculado",
#     )

#     class Meta:
#         model = MinutaLigacaoAto
#         fields = ["minuta_exigencia", "ato_id"]
