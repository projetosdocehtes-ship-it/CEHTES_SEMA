from django.urls import path

from apps.minutas.views import (
    MinutaCreateView,
    MinutaDeleteView,
    MinutaDetailView,
    MinutaListView,
    MinutaUpdateView,
)

app_name = "minutas"

urlpatterns = [
    path("", MinutaListView.as_view(), name="minuta_list"),
    path("<int:pk>/", MinutaDetailView.as_view(), name="minuta_detail"),
    path("new/", MinutaCreateView.as_view(), name="minuta_create"),
    path("<int:pk>/edit/", MinutaUpdateView.as_view(), name="minuta_edit"),
    path(
        "<int:pk>/delete/",
        MinutaDeleteView.as_view(),
        name="minuta_delete",
    ),
]
