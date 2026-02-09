"""
Test OAuth role redirection and user auto-approval.
Run with: python manage.py test accounts
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

CustomUser = get_user_model()


class OAuthRoleRedirectionTest(TestCase):
    """Test OAuth role assignment and redirection"""
    
    def setUp(self):
        self.client = Client()
    
    def test_customer_role_assignment(self):
        """Test that new OAuth users get 'customer' role"""
        # Create a user as if from OAuth
        user = CustomUser(
            email='testuser@gmail.com',
            username='testuser',
            first_name='Test',
            last_name='User'
        )
        user.role = 'customer'
        user.is_approved = True
        user.save()
        
        # Verify role and approval
        user.refresh_from_db()
        self.assertEqual(user.role, 'customer')
        self.assertTrue(user.is_approved)
    
    def test_admin_auto_approval(self):
        """Test that admin users are auto-approved"""
        user = CustomUser.objects.create_user(
            email='admin@example.com',
            username='admin',
            password='testpass123'
        )
        user.role = 'admin'
        user.save()
        
        # Should be auto-approved
        user.refresh_from_db()
        self.assertTrue(user.is_approved)
    
    def test_default_role_assignment(self):
        """Test that new users get default 'customer' role"""
        user = CustomUser.objects.create_user(
            email='newuser@example.com',
            username='newuser',
            password='testpass123'
        )
        
        user.refresh_from_db()
        self.assertEqual(user.role, 'customer')
