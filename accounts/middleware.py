from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse
from django.conf import settings

class RoleMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        if request.user.is_authenticated:
            # Only update session if values have changed (prevent unnecessary DB writes)
            current_role = request.session.get('user_role')
            current_approved = request.session.get('is_approved')
            
            if current_role != request.user.role or current_approved != request.user.is_approved:
                request.session['user_role'] = request.user.role
                request.session['is_approved'] = request.user.is_approved
            
            # Admin portal access control
            if 'admin' in request.path and not request.path.startswith('/admin/') and request.user.role != 'admin':
                messages.error(request, 'Access to admin portal denied.')
                return redirect('home')
                
        response = self.get_response(request)
        return response