from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.edit import UpdateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import JsonResponse
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
    Determine redirect URL based on user role or specific email.
    Admins → Admin Dashboard
    Staff → Staff Inventory Management
    """
    if user.email == 'themannancrackers@gmail.com' or user.role == 'admin':
        return reverse_lazy('inventory:admin_dashboard')
    elif user.email == 'staff@mannancrackers.com' or user.role == 'staff':
        return reverse_lazy('inventory:staff_inventory')
    else:
        return reverse_lazy('inventory:home')


@login_required
def role_based_redirect(request):
    """
    Redirect authenticated users to their role-specific dashboard.
    Useful for redirecting after login to appropriate page.
    """
    redirect_url = get_role_redirect_url(request.user)
    return redirect(redirect_url)
