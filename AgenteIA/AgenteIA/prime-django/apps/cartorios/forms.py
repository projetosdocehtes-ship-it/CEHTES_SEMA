# forms.py
import logging

from django import forms
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.contrib.auth.models import User

from apps.cartorios.models import Usuario

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")


class AdminPasswordChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField(
        label="Password",
        help_text=(
            "Raw passwords are not stored, so there is no way to see this "
            "users password, but you can change the password using "
            '<a href="../password/">this form</a>.'
        ),
    )

    class Meta:
        model = User
        fields = ["password"]

    def clean_password(self):
        # Regardless of what the user provides, return the initial value.
        # This is done here, rather than on the field, because the
        # field does not have access to the initial value
        return self.initial["password"]


class UsuarioAdminChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField(
        label="Password",
        help_text=(
            "Raw passwords are not stored, so there is no way to see this "
            "users password, but you can change the password using "
            '<a href="../password/">this form</a>.'
        ),
    )

    class Meta:
        model = Usuario
        fields = ("username", "password", "is_active", "is_staff", "is_superuser")

    def clean_password(self):
        return self.initial["password"]


class UsuarioAdminCreationForm(forms.ModelForm):
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(
        label="Password confirmation",
        widget=forms.PasswordInput,
    )

    class Meta:
        model = Usuario
        fields = ("username", "email")

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            msg = "Passwords don't match"
            raise forms.ValidationError(msg)
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user
