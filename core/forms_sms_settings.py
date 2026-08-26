from django import forms
from core.models import SmsSettings


class SmsSettingsForm(forms.ModelForm):
    class Meta:
        model = SmsSettings
        fields = [
            "provider_name",
            "api_key",
            "sender_name",
            "enable_absence",
            "enable_paiement",
            "enable_impaye",
            "optin_default",
            "quiet_start",
            "quiet_end",
        ]
        widgets = {
            "api_key": forms.PasswordInput(render_value=True, attrs={"autocomplete": "off"}),
            "quiet_start": forms.TimeInput(attrs={"type": "time"}),
            "quiet_end": forms.TimeInput(attrs={"type": "time"}),
        }
