from django.shortcuts import redirect

class SimplePasswordAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        # Allow access to login, admin panel, and static assets
        if path.startswith('/admin/') or path == '/login/' or path.startswith('/static/'):
            return self.get_response(request)

        # Check for authentication flag in session
        if not request.session.get('is_logged_in'):
            return redirect('/login/')

        return self.get_response(request)
