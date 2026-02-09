"""
Unit Tests for WhatsApp Notifications
Tests client, service, and signal integration
"""

import json
from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from django.conf import settings
from inventory.models import Order, Product, Category, OrderItem
from accounts.models import CustomUser
from .whatsapp_client import WhatsAppClient
from .service import (
    send_order_confirmation_to_customer,
    send_order_notification_to_admin,
    send_order_notifications,
    format_order_items,
)


class WhatsAppClientTestCase(TestCase):
    """Test cases for WhatsAppClient class"""

    @override_settings(
        WHATSAPP_DRY_RUN=True,
        WHATSAPP_PHONE_NUMBER_ID='1234567890',
        WHATSAPP_ACCESS_TOKEN='test_token',
        WHATSAPP_API_VERSION='v18.0'
    )
    def test_dry_run_mode_enabled(self):
        """Test that dry-run mode logs message without API call"""
        client = WhatsAppClient()
        
        result = client.send_text("+919876543210", "Test message")
        
        self.assertTrue(result['success'])
        self.assertEqual(result['mode'], 'dry_run')
        self.assertIn('payload', result)
        self.assertEqual(result['to'], "+919876543210")

    @override_settings(
        WHATSAPP_DRY_RUN=True,
        WHATSAPP_PHONE_NUMBER_ID='1234567890',
        WHATSAPP_ACCESS_TOKEN='test_token',
        WHATSAPP_API_VERSION='v18.0'
    )
    def test_invalid_phone_number(self):
        """Test validation of phone number format"""
        client = WhatsAppClient()
        
        # Missing + prefix
        result = client.send_text("919876543210", "Test message")
        self.assertFalse(result['success'])
        self.assertIn("must start with '+'", result['error'])
        
        # Non-digit characters
        result = client.send_text("+91ABCD12345", "Test message")
        self.assertFalse(result['success'])
        self.assertIn("only digits", result['error'])

    @override_settings(
        WHATSAPP_DRY_RUN=True,
        WHATSAPP_PHONE_NUMBER_ID='1234567890',
        WHATSAPP_ACCESS_TOKEN='test_token',
        WHATSAPP_API_VERSION='v18.0'
    )
    def test_empty_message_body(self):
        """Test that empty message is rejected"""
        client = WhatsAppClient()
        
        result = client.send_text("+919876543210", "")
        self.assertFalse(result['success'])
        self.assertIn("cannot be empty", result['error'])

    @override_settings(
        WHATSAPP_DRY_RUN=True,
        WHATSAPP_PHONE_NUMBER_ID='1234567890',
        WHATSAPP_ACCESS_TOKEN='test_token',
        WHATSAPP_API_VERSION='v18.0'
    )
    def test_payload_structure(self):
        """Test that API payload is correctly structured"""
        client = WhatsAppClient()
        
        result = client.send_text("+919876543210", "Test message")
        payload = result['payload']
        
        self.assertEqual(payload['messaging_product'], 'whatsapp')
        self.assertEqual(payload['to'], '+919876543210')
        self.assertEqual(payload['type'], 'text')
        self.assertEqual(payload['text']['body'], 'Test message')
        self.assertFalse(payload['text']['preview_url'])

    @override_settings(
        WHATSAPP_DRY_RUN=False,
        WHATSAPP_PHONE_NUMBER_ID='1234567890',
        WHATSAPP_ACCESS_TOKEN='test_token',
        WHATSAPP_API_VERSION='v18.0'
    )
    @patch('whatsapp_notifications.whatsapp_client.requests.post')
    def test_production_api_success(self, mock_post):
        """Test successful API call in production mode"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'messages': [{'id': 'wamid.test123'}]
        }
        mock_post.return_value = mock_response
        
        client = WhatsAppClient()
        result = client.send_text("+919876543210", "Test message")
        
        self.assertTrue(result['success'])
        self.assertEqual(result['mode'], 'production')
        self.assertEqual(result['message_id'], 'wamid.test123')
        mock_post.assert_called_once()

    @override_settings(
        WHATSAPP_DRY_RUN=False,
        WHATSAPP_PHONE_NUMBER_ID='1234567890',
        WHATSAPP_ACCESS_TOKEN='test_token',
        WHATSAPP_API_VERSION='v18.0'
    )
    @patch('whatsapp_notifications.whatsapp_client.requests.post')
    def test_production_api_failure(self, mock_post):
        """Test API error handling in production mode"""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = 'Invalid request'
        mock_post.return_value = mock_response
        
        client = WhatsAppClient()
        result = client.send_text("+919876543210", "Test message")
        
        self.assertFalse(result['success'])
        self.assertEqual(result['mode'], 'production')
        self.assertIn("status 400", result['error'])

    @override_settings(
        WHATSAPP_DRY_RUN=False,
        WHATSAPP_PHONE_NUMBER_ID='1234567890',
        WHATSAPP_ACCESS_TOKEN='test_token',
        WHATSAPP_API_VERSION='v18.0'
    )
    @patch('whatsapp_notifications.whatsapp_client.requests.post')
    def test_production_timeout(self, mock_post):
        """Test timeout handling in production mode"""
        import requests
        mock_post.side_effect = requests.Timeout("Connection timeout")
        
        client = WhatsAppClient()
        result = client.send_text("+919876543210", "Test message")
        
        self.assertFalse(result['success'])
        self.assertIn("timeout", result['error'])


class OrderNotificationServiceTestCase(TestCase):
    """Test cases for order notification service"""

    def setUp(self):
        """Set up test data"""
        # Create category
        self.category = Category.objects.create(
            name="Test Category",
            description="Test"
        )
        
        # Create product
        self.product = Product.objects.create(
            name="Test Product",
            category=self.category,
            price=1000,
            stock_quantity=10,
            description="Test product"
        )
        
        # Create test user
        self.user = CustomUser.objects.create_user(
            email='test@example.com',
            first_name='Test',
            last_name='User'
        )

    @override_settings(
        WHATSAPP_DRY_RUN=True,
        WHATSAPP_PHONE_NUMBER_ID='1234567890',
        WHATSAPP_ACCESS_TOKEN='test_token',
        WHATSAPP_API_VERSION='v18.0'
    )
    def test_format_order_items(self):
        """Test formatting of order items"""
        order = Order.objects.create(
            user=self.user,
            full_name='John Doe',
            email='john@example.com',
            phone='9876543210',
            address='123 Main St',
            total_amount=5000,
            status='pending'
        )
        
        OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=2,
            price=1000
        )
        
        items_str = format_order_items(order)
        self.assertIn("Test Product", items_str)
        self.assertIn("x2", items_str)

    @override_settings(
        WHATSAPP_DRY_RUN=True,
        WHATSAPP_PHONE_NUMBER_ID='1234567890',
        WHATSAPP_ACCESS_TOKEN='test_token',
        WHATSAPP_API_VERSION='v18.0'
    )
    def test_send_order_confirmation_to_customer(self):
        """Test customer confirmation message"""
        order = Order.objects.create(
            user=self.user,
            full_name='John Doe',
            email='john@example.com',
            phone='9876543210',
            address='123 Main St',
            total_amount=5000,
            status='pending'
        )
        
        OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=2,
            price=1000
        )
        
        result = send_order_confirmation_to_customer(order)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['recipient_type'], 'customer')
        self.assertEqual(result['order_id'], order.id)

    @override_settings(
        WHATSAPP_DRY_RUN=True,
        WHATSAPP_PHONE_NUMBER_ID='1234567890',
        WHATSAPP_ACCESS_TOKEN='test_token',
        WHATSAPP_API_VERSION='v18.0',
        WHATSAPP_ADMIN_NUMBER='+919999999999'
    )
    def test_send_order_notification_to_admin(self):
        """Test admin notification message"""
        order = Order.objects.create(
            user=self.user,
            full_name='John Doe',
            email='john@example.com',
            phone='9876543210',
            address='123 Main St',
            total_amount=5000,
            status='pending'
        )
        
        OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=2,
            price=1000
        )
        
        result = send_order_notification_to_admin(order)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['recipient_type'], 'admin')
        self.assertEqual(result['order_id'], order.id)

    @override_settings(
        WHATSAPP_DRY_RUN=True,
        WHATSAPP_PHONE_NUMBER_ID='1234567890',
        WHATSAPP_ACCESS_TOKEN='test_token',
        WHATSAPP_API_VERSION='v18.0',
        WHATSAPP_ADMIN_NUMBER='+919999999999'
    )
    def test_send_order_notifications_both(self):
        """Test sending notifications to both customer and admin"""
        order = Order.objects.create(
            user=self.user,
            full_name='John Doe',
            email='john@example.com',
            phone='9876543210',
            address='123 Main St',
            total_amount=5000,
            status='pending'
        )
        
        OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=2,
            price=1000
        )
        
        results = send_order_notifications(order)
        
        self.assertEqual(results['order_id'], order.id)
        self.assertTrue(results['customer']['success'])
        self.assertTrue(results['admin']['success'])
        self.assertEqual(results['customer']['recipient_type'], 'customer')
        self.assertEqual(results['admin']['recipient_type'], 'admin')
