"""Copyright (c) 2019 - present AppSeed.us."""

from django import template
from django.contrib.auth import logout
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.template import loader
from django.urls import reverse

from apps import COMMON

# from apps.authentication.models import CustomUser
from apps.cartorios.models import Usuario as CustomUser


def index(request):
    if (
        CustomUser.objects.get(username=request.user.username).status
        == COMMON.USER_SUSPENDED
    ):
        logout(request)
        return redirect(
            reverse("login") + "?message=Suspended account. Please contact support.",
        )
    context = {"segment": "index"}

    html_template = loader.get_template("samples/index.html")
    return HttpResponse(html_template.render(context, request))


def pages(request):
    context = {}
    # All resource paths end in .html.
    # Pick out the html file name from the url. And load that template.
    try:
        load_template = request.path.split("/")[-1]

        if load_template == "admin":
            return HttpResponseRedirect(reverse("admin:index"))
        context["segment"] = load_template

        html_template = loader.get_template("samples/" + load_template)
        return HttpResponse(html_template.render(context, request))

    except template.TemplateDoesNotExist:
        html_template = loader.get_template("404.html")
        return HttpResponse(html_template.render(context, request))

    except Exception:
        html_template = loader.get_template("samples/page-500.html")
        return HttpResponse(html_template.render(context, request))
