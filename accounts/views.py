from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.edit import UpdateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import JsonResponse
from allauth.socialaccount.models import SocialAccount
from .models import CustomUser


@login_required
def profile_view(request):
    return render(request, 'accounts/profile.html', {'user': request.user})

class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = CustomUser
    template_name = 'accounts/profile_update.html'
    fields = ['phone_number', 'address', 'profile_picture', 'date_of_birth']
    success_url = reverse_lazy('accounts:profile')

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, 'Your profile has been updated successfully!')
        return super().form_valid(form)


def get_role_redirect_url(user):
    """
    Determine redirect URL based on user role.
    Admins → Admin Dashboard
    Staff → Staff Inventory Management
    Customers → Home Page
    """
    if user.role == 'admin':
        return reverse_lazy('inventory:admin_dashboard')
    elif user.role == 'staff':
        return reverse_lazy('inventory:staff_inventory')
    else:
        return reverse_lazy('inventory:home')


def handle_oauth_login(user):
    """
    Handle OAuth user role assignment and approval.
    - New OAuth users default to 'customer' role
    - Auto-approve admins
    - Set is_approved flag for staff/customers
    """
    # Check if this is a new OAuth signup
    try:
        social_account = SocialAccount.objects.get(user=user)
        
        # Only process on first OAuth login (when role is still 'customer' default)
        if user.role == 'customer' and not user.is_approved:
            # Auto-approve customers from OAuth
            user.is_approved = True
            user.save()
            
            messages.info(
                None, 
                f'Welcome {user.email}! Your account has been created and auto-approved.'
            )
    except SocialAccount.DoesNotExist:
        pass


def oauth_callback_redirect(request):
    """
    Redirect users after OAuth login based on their role.
    This can be called from a custom OAuth callback.
    """
    if not request.user.is_authenticated:
        return redirect('account_login')
    
    user = request.user
    
    # Handle new OAuth user
    if hasattr(user, 'socialaccount_set') and user.socialaccount_set.exists():
        handle_oauth_login(user)
    
    # Redirect based on role
    redirect_url = get_role_redirect_url(user)
    return redirect(redirect_url)


@login_required
def role_based_redirect(request):
    """
    Redirect authenticated users to their role-specific dashboard.
    Useful for redirecting after login to appropriate page.
    """
    redirect_url = get_role_redirect_url(request.user)
    return redirect(redirect_url)
