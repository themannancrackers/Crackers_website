from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('profile/', views.profile_view, name='profile'),
    path('profile/update/', views.ProfileUpdateView.as_view(), name='profile_update'),
    path('oauth/callback/', views.oauth_callback_redirect, name='oauth_callback'),
    path('redirect/', views.role_based_redirect, name='role_redirect'),
]