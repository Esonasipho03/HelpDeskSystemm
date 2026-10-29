from django.utils.cache import add_never_cache_headers


class NoStoreForLoggedInPagesMiddleware:
    """Pages are personal (each role sees a different dashboard), so the browser
    must not keep them. Without this, pressing Back after logging out and in as
    someone else can show the previous user's page from the browser cache."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        user = getattr(request, "user", None)
        content_type = response.get("Content-Type", "")
        if user is not None and user.is_authenticated and content_type.startswith("text/html"):
            add_never_cache_headers(response)   # Cache-Control: no-cache, no-store, must-revalidate, private
        return response
