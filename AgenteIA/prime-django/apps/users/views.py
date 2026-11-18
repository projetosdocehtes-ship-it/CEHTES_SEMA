from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password
from django.shortcuts import get_object_or_404, redirect, render

from apps.users.forms import QuillFieldForm
from apps.users.models import Profile

# Create your views here.


@login_required(login_url="/accounts/login-v1/")
def profile(request):
    profile = get_object_or_404(Profile, user=request.user)
    form = QuillFieldForm(instance=profile)
    if request.method == "POST":
        if request.POST.get("email"):
            request.user.email = request.POST.get("email")
            request.user.save()

        for attribute, value in request.POST.items():
            if attribute == "csrfmiddlewaretoken":
                continue

            setattr(profile, attribute, value)
            profile.save()

        messages.success(request, "Profile updated successfully")
        return redirect(request.headers.get("referer"))

    context = {"segment": "profile", "form": form}
    return render(request, "pages/apps/user-profile.html", context)


def upload_avatar(request):
    profile = get_object_or_404(Profile, user=request.user)
    if request.method == "POST":
        profile.avatar = request.FILES.get("avatar")
        profile.save()
        messages.success(request, "Avatar uploaded successfully")
    return redirect(request.headers.get("referer"))


def change_password(request):
    user = request.user
    if request.method == "POST":
        new_password = request.POST.get("new_password")
        confirm_new_password = request.POST.get("confirm_new_password")

        if new_password == confirm_new_password:
            if check_password(request.POST.get("current_password"), user.password):
                user.set_password(new_password)
                user.save()
                messages.success(request, "Password changed successfully")
            else:
                messages.error(request, "Old password doesn't match!")
        else:
            messages.error(request, "Password doesn't match!")

    return redirect(request.headers.get("referer"))


@login_required(login_url="/accounts/login-v1/")
def change_mode(request):
    profile = get_object_or_404(Profile, user=request.user)
    if profile.dark_mode:
        profile.dark_mode = False
    else:
        profile.dark_mode = True

    profile.save()

    return redirect(request.headers.get("referer"))
