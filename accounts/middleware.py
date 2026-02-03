from .threadlocal import set_current_user

class CurrentUserMiddleware:
    """
    Stocke le user connecté dans un threadlocal pour l'utiliser dans les models.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        set_current_user(getattr(request, "user", None))
        return self.get_response(request)
