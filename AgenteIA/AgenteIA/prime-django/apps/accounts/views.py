"""Copyright (c) 2019 - present AppSeed.us."""

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from apps import COMMON
from apps.accounts.forms import EditProfileForm

# from apps.authentication.models import CustomUser
from apps.cartorios.models import Usuario as CustomUser
from apps.helpers import *


@login_required(login_url="/login/")
def user_list(request, **kwargs):
    # get all users
    if request.method == "GET":
        users = CustomUser.objects.all()
        form = EditProfileForm()
        return render(
            request,
            "accounts/user-list.html",
            context={
                "users": [
                    {
                        "fullname": user.fullname or user.username or "Sem nome",
                        "bio": user.bio,
                        "email": user.email or "(Sem email)",
                        "phone": user.phone,
                        "website": user.website,
                        "username": user.username,
                        "zipcode": user.zipcode,
                        "address": user.address,
                        "registration_date": user.registration_date,
                        "status": 0 if user.status == COMMON.USER_SUSPENDED else 1,
                        "image": user.image,
                    }
                    for user in users
                ],
                "form": form,
            },
        )

    # Update Profile
    if request.method == "POST":
        return profile(request, **kwargs)

    if request.method == "PUT":
        user = CustomUser.objects.get(username=kwargs.get("username"))

        if user.status == COMMON.USER_ACTIVE:
            user.status = COMMON.USER_SUSPENDED
        else:
            user.status = COMMON.USER_ACTIVE

        user.failed_logins = 0
        user.save()
        return JsonResponse({})

    if request.method == "DELETE":
        try:
            user = CustomUser.objects.filter(username=kwargs.get("username")).first()

            if user.is_superuser:
                msg = "Cannot delete superuser"
                raise Exception(msg)

            user.delete()

        except Exception as e:
            return JsonResponse({"errors": str(e)}, status=400)
        return JsonResponse({})
    return None


@login_required(login_url="/login/")
def profile(request, **kwargs):
    user = CustomUser.objects.get(username=request.user.username)
    context = get_user_context(request, user)
    password_form = PasswordChangeForm(user=request.user)

    # if request.method == "GET":
    #     return render(request, "accounts/user-profile.html", context)

    if request.method == "POST":
        if "change_password" in request.POST:
            # Tratando o formulário de alteração de senha
            password_form = PasswordChangeForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                user = password_form.save()
                user.last_password_change = timezone.now()
                user.save()
                update_session_auth_hash(request, user)
                messages.success(request, "A senha foi alterada.")
            else:
                for error in password_form.errors:
                    messages.error(request, password_form.errors[error])

        elif "edit_profile" in request.POST:
            # Tratando o formulário de edição do perfil
            form = EditProfileForm(
                request.POST,
                instance=user,
            )
            if form.is_valid():
                user = form.save()
                # Código para tratamento de imagem, FTP, etc.
                messages.success(request, "Perfil atualizado!")
            else:
                for error in form.errors:
                    messages.error(request, form.errors[error])

    context["password_form"] = password_form
    # context["form"] = form
    context["user"] = user
    return render(request, "accounts/user-profile.html", context)


def get_user_context(request, user):
    # social_acc = user.socialaccount_set.first()
    # if social_acc:
    #     user.image = social_acc.get_avatar_url()

    return {
        "is_authenticated": request.user.is_authenticated,
        "user": {
            "cartorio": user.cartorio,
            "fullname": user.fullname,
            "bio": user.bio,
            "email": user.email,
            "phone": user.phone,
            "website": user.website,
            "zipcode": user.zipcode,
            "address": user.address,
            "image": user.image,
            "username": user.username,
            # "login_with_oauth": social_acc is not None,
            "is_authenticated": request.user.is_authenticated,
            # "provider": social_acc.provider if social_acc is not None else None,
        },
    }
