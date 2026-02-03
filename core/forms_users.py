# core/forms_users.py
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

User = get_user_model()


from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

User = get_user_model()

class UserCreateForm(forms.ModelForm):
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple
    )
    auto_password = forms.BooleanField(required=False, initial=True, label="Générer un mot de passe automatiquement")
    password = forms.CharField(required=False, widget=forms.PasswordInput, label="Mot de passe (si auto désactivé)")

    class Meta:
        model = User
        fields = ["username", "last_name", "first_name", "email", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["groups"].queryset = Group.objects.all().order_by("name")

    def clean(self):
        cleaned = super().clean()
        auto = cleaned.get("auto_password")
        pwd = (cleaned.get("password") or "").strip()
        if not auto and len(pwd) < 6:
            raise forms.ValidationError("Si auto désactivé, le mot de passe doit contenir au moins 6 caractères.")
        return cleaned


class UserUpdateForm(forms.ModelForm):
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = User
        fields = ["username", "last_name", "first_name", "email", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["groups"].queryset = Group.objects.all().order_by("name")


class PasswordChangeForm(forms.Form):
    auto_password = forms.BooleanField(required=False, initial=True, label="Générer un mot de passe automatiquement")
    password = forms.CharField(required=False, widget=forms.PasswordInput, label="Nouveau mot de passe")

    def clean(self):
        cleaned = super().clean()
        auto = cleaned.get("auto_password")
        pwd = cleaned.get("password") or ""
        if not auto and len(pwd.strip()) < 6:
            raise forms.ValidationError("Mot de passe trop court (min 6).")
        return cleaned
