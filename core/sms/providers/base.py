from typing import Tuple


class BaseSmsProvider:
    """
    Interface provider SMS.
    Retour: (ok: bool, provider_message_id: str, error: str)
    """

    def __init__(self, api_key: str = "", sender: str = ""):
        self.api_key = api_key
        self.sender = sender

    def send(self, to_phone: str, message: str) -> Tuple[bool, str, str]:
        raise NotImplementedError
