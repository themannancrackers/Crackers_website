from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('staff', 'Staff'),
        ('customer', 'Customer'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')
    is_approved = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    date_of_birth = models.DateField(null=True, blank=True)
    
    class Meta:
        permissions = [
            ("can_view_inventory", "Can view inventory"),
            ("can_manage_inventory", "Can manage inventory"),
            ("can_approve_users", "Can approve users"),
        ]

    def save(self, *args, **kwargs):
        # Auto-approve admins
        if self.role == 'admin':
            self.is_approved = True
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('profile')
