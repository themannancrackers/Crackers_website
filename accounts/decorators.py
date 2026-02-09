from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps
from django.http import HttpResponseForbidden

def role_required(allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, 'Please log in to access this page.')
                return redirect('account_login')
            
            if request.user.role in allowed_roles:
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, 'You do not have permission to access this page.')
                return HttpResponseForbidden('Access Denied')
            
        return _wrapped_view
    return decorator

def admin_required(view_func):
    return role_required(['admin'])(view_func)

def staff_required(view_func):
    return role_required(['admin', 'staff'])(view_func)

def approved_user_required(view_func):
    return role_required(['admin', 'staff', 'customer'])(view_func)