from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission

User = get_user_model()

class RoleBasedBackend(ModelBackend):
    def get_user_permissions(self, user_obj, obj=None):
        if not user_obj.is_active or user_obj.is_anonymous:
            return set()
        
        # Get default permissions
        permissions = super().get_user_permissions(user_obj, obj)
        
        # Add role-based permissions
        if user_obj.role == 'admin':
            admin_perms = Permission.objects.all()
            permissions.update(perm.codename for perm in admin_perms)
        elif user_obj.role == 'staff':
            if user_obj.is_approved:
                staff_perms = ['can_view_inventory', 'can_manage_inventory']
                permissions.update(staff_perms)
        elif user_obj.role == 'customer':
            if user_obj.is_approved:
                customer_perms = ['can_view_inventory']
                permissions.update(customer_perms)
        
        return permissions