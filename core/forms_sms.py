from django import forms
from core.models_sms import SmsTemplate


class SmsTemplateForm(forms.ModelForm):
    class Meta:
        model = SmsTemplate
        fields = ["nom", "code", "type_template", "contenu", "is_active"]
        widgets = {
            "nom": forms.TextInput(attrs={"class": "az-input", "placeholder": "Ex: Absence info"}),
            "code": forms.TextInput(attrs={"class": "az-input", "placeholder": "absence_info"}),
            "type_template": forms.Select(attrs={"class": "az-input"}),
            "contenu": forms.Textarea(attrs={"class": "az-textarea", "rows": 5}),
            "is_active": forms.CheckboxInput(attrs={"class": "az-checkbox"}),
        }
