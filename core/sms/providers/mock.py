from typing import Tuple
from .base import BaseSmsProvider


class MockProvider(BaseSmsProvider):
    """
    Provider de test : ne fait rien mais simule un succès.
    """

    def send(self, to_phone: str, message: str) -> Tuple[bool, str, str]:
        if not to_phone or not message:
            return (False, "", "Numéro ou message vide")
        return (True, "mock-id", "")
