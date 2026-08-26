from typing import Tuple
from .base import BaseSmsProvider

try:
    from twilio.rest import Client
except Exception:  # pragma: no cover
    Client = None


class TwilioProvider(BaseSmsProvider):
    def send(self, to_phone: str, message: str) -> Tuple[bool, str, str]:
        if not Client:
            return (False, "", "Twilio non installé")

        if not self.api_key:
            return (False, "", "API Key Twilio manquante")

        # api_key attendu sous forme SID|TOKEN
        try:
            sid, token = self.api_key.split("|", 1)
        except ValueError:
            return (False, "", "API Key Twilio doit être SID|TOKEN")

        try:
            client = Client(sid, token)
            msg = client.messages.create(
                body=message,
                from_=self.sender or None,
                to=to_phone
            )
            return (True, msg.sid, "")
        except Exception as e:
            return (False, "", str(e))
