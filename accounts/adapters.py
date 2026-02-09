"""
Custom OAuth adapters for handling role assignment, linking, and auto-approval.
"""
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model

CustomUser = get_user_model()


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom adapter for Google OAuth:
    - Links existing users by email (prevents /3rdparty/signup/)
    - Assigns default role='customer' for new users
    - Auto-approves OAuth users
    """

    def pre_social_login(self, request, sociallogin):
        """
        Runs right after Google authenticates but before user login/signup.
        Links OAuth account to existing user by email if found.
        """
        if request.user.is_authenticated:
            return  # user already logged in, nothing to do

        email = sociallogin.account.extra_data.get("email", "").lower()
        if not email:
            return

        try:
            existing_user = CustomUser.objects.get(email__iexact=email)
            # Link this social account to the existing user
            sociallogin.connect(request, existing_user)
        except CustomUser.DoesNotExist:
            # New user will go through populate_user()
            pass

    def populate_user(self, request, sociallogin, data):
        """
        Called when creating a brand-new OAuth user.
        """
        user = super().populate_user(request, sociallogin, data)
        if not user.pk:
            user.role = "customer"
            user.is_approved = True
        return user
