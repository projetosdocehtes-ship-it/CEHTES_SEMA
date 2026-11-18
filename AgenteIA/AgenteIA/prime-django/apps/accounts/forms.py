"""Copyright (c) 2019 - present AppSeed.us."""

from django import forms

# from apps.authentication.models import CustomUser
from apps.cartorios.models import Usuario as CustomUser


class EditProfileForm(forms.ModelForm):
    # email = forms.
    class Meta:
        model = CustomUser
        fields = ("email", "phone", "website", "address", "zipcode", "bio")
