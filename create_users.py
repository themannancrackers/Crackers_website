import os
import django

# Provide the correct settings module path for your Django project
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crackers_ecommerce.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# ================================
# 1. Admin Account
# ================================
admin_email = "themannancrackers@gmail.com"
admin_pass = "Admin@123!"

admin_user, admin_created = User.objects.get_or_create(
    username=admin_email,
    defaults={'email': admin_email}
)
admin_user.set_password(admin_pass)
admin_user.is_staff = True
admin_user.is_superuser = True
admin_user.role = 'admin'
admin_user.is_approved = True
admin_user.save()

status = "Created" if admin_created else "Updated"
print(f"[{status}] Admin User: {admin_email} | Password: {admin_pass}")

# ================================
# 2. Staff Account
# ================================
staff_email = "staff@mannancrackers.com"
staff_pass = "Staff@123!"

staff_user, staff_created = User.objects.get_or_create(
    username=staff_email,
    defaults={'email': staff_email}
)
staff_user.set_password(staff_pass)
staff_user.is_staff = True
staff_user.is_superuser = False
staff_user.role = 'staff'
staff_user.is_approved = True
staff_user.save()

status = "Created" if staff_created else "Updated"
print(f"[{status}] Staff User: {staff_email} | Password: {staff_pass}")
