from importlib import import_module

from django.apps import apps
from django.urls import path

apps_dict = {}


def get_patterns(apps_dict):
    """
    apps_dict['app_name'] = {
        'app_name': 'app_name',
        'filename': 'views'
    }
    """
    urlpatterns = []
    for key, value in apps_dict.items():
        app_module = import_module("{}.{}".format(value["app_name"], value["filename"]))
        app_models = apps.get_app_config(value["app_name"]).get_models()
        for model in app_models:
            app_name = model._meta.app_label
            model_name = model.__name__
            model_name_lower = model.__name__.lower()
            listview = hasattr(app_module, f"{model_name}ListView")
            if listview:
                listview = getattr(app_module, f"{model_name}ListView").as_view()
                urlpatterns += [
                    path(
                        f"{app_name}/{model_name_lower}/",
                        listview,
                        name=f"{app_name}-{model_name_lower}-list",
                    ),
                ]
            detailview = hasattr(app_module, f"{model_name}DetailView")
            if detailview:
                detailview = getattr(app_module, f"{model_name}DetailView").as_view()
                urlpatterns += [
                    path(
                        f"{app_name}/{model_name_lower}/<int:pk>/detail/",
                        detailview,
                        name=f"{app_name}-{model_name_lower}-detail",
                    ),
                ]
            addview = hasattr(app_module, f"{model_name}CreateView")
            if addview:
                addview = getattr(app_module, f"{model_name}CreateView").as_view()
                urlpatterns += [
                    path(
                        f"{app_name}/{model_name_lower}/add/",
                        addview,
                        name=f"{app_name}-{model_name_lower}-create",
                    ),
                ]
            updateview = hasattr(app_module, f"{model_name}UpdateView")
            if updateview:
                updateview = getattr(app_module, f"{model_name}UpdateView").as_view()
                urlpatterns += [
                    path(
                        f"{app_name}/{model_name_lower}/<int:pk>/",
                        updateview,
                        name=f"{app_name}-{model_name_lower}-update",
                    ),
                ]
            deleteview = hasattr(app_module, f"{model_name}DeleteView")
            if deleteview:
                deleteview = getattr(app_module, f"{model_name}DeleteView").as_view()
                urlpatterns += [
                    path(
                        f"{app_name}/{model_name_lower}/<int:pk>/delete/",
                        deleteview,
                        name=f"{app_name}-{model_name_lower}-delete",
                    ),
                ]
    return urlpatterns
