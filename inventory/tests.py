from datetime import datetime, timezone as datetime_timezone
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import CustomUser
from .models import Category, Order, OrderItem, Product, SiteConfiguration


class InventoryWorkflowTests(TestCase):
	def setUp(self):
		SiteConfiguration.objects.create(min_order_amount=Decimal('1999.00'))
		self.category = Category.objects.create(
			name='Rocket Crackers',
			description='Outdoor celebration products',
		)
		self.product = Product.objects.create(
			name='Display Rocket',
			category=self.category,
			price=Decimal('1000.00'),
			stock_quantity=5,
			description='A bright outdoor rocket display',
		)
		self.staff = CustomUser.objects.create_user(
			username='staff',
			password='test-password',
			role='staff',
			is_approved=True,
		)

	def create_order(self, status='pending', quantity=2, user=None):
		order = Order.objects.create(
			user=user,
			full_name='Test Customer',
			email='customer@example.com',
			phone='9894835855',
			address='12 Test Street',
			total_amount=Decimal('2000.00'),
			status=status,
		)
		OrderItem.objects.create(
			order=order,
			product=self.product,
			quantity=quantity,
			price=self.product.price,
		)
		return order

	@patch('inventory.views.utils.send_order_confirmation')
	def test_checkout_creates_pending_order_and_decrements_stock(self, send_email):
		response = self.client.post(
			reverse('inventory:checkout'),
			data={
				'customerData': {
					'fullName': 'Checkout Customer',
					'email': 'checkout@example.com',
					'phone': '9894835855',
					'deliveryAddress': '12 Checkout Street',
				},
				'cartItems': {
					str(self.product.id): {
						'name': self.product.name,
						'quantity': 2,
						'price': '1000.00',
					}
				},
			},
			content_type='application/json',
		)

		self.assertEqual(response.status_code, 201)
		order = Order.objects.get(id=response.json()['order_id'])
		self.assertEqual(order.status, 'pending')
		self.assertEqual(order.items.count(), 1)
		self.product.refresh_from_db()
		self.assertEqual(self.product.stock_quantity, 3)
		send_email.assert_not_called()

	def test_pending_order_can_be_deleted_and_stock_is_restored(self):
		order = self.create_order()
		self.client.force_login(self.staff)

		response = self.client.post(
			reverse('inventory:delete_order', args=[order.id])
		)

		self.assertEqual(response.status_code, 200)
		self.assertTrue(response.json()['success'])
		self.assertFalse(Order.objects.filter(id=order.id).exists())
		self.product.refresh_from_db()
		self.assertEqual(self.product.stock_quantity, 7)

	def test_non_pending_order_cannot_be_deleted(self):
		order = self.create_order(status='processing')
		self.client.force_login(self.staff)

		response = self.client.post(
			reverse('inventory:delete_order', args=[order.id])
		)

		self.assertEqual(response.status_code, 400)
		self.assertFalse(response.json()['success'])
		self.assertTrue(Order.objects.filter(id=order.id).exists())

	def test_staff_order_search_matches_product_name_and_email(self):
		order = self.create_order()
		self.client.force_login(self.staff)

		product_response = self.client.get(
			reverse('inventory:staff_orders'), {'q': 'Display Rocket'}
		)
		email_response = self.client.get(
			reverse('inventory:staff_orders'), {'q': 'customer@example.com'}
		)

		self.assertContains(product_response, 'Test Customer')
		self.assertContains(email_response, 'Test Customer')
		self.assertContains(product_response, f'ORD-{order.id:06d}')

	def test_staff_inventory_search_matches_category_and_description(self):
		self.client.force_login(self.staff)

		category_response = self.client.get(
			reverse('inventory:staff_inventory'), {'search': 'Rocket Crackers'}
		)
		description_response = self.client.get(
			reverse('inventory:staff_inventory'), {'search': 'bright outdoor'}
		)

		self.assertContains(category_response, 'Display Rocket')
		self.assertContains(description_response, 'Display Rocket')

	@override_settings(TIME_ZONE='Asia/Kolkata')
	def test_staff_orders_render_order_time_in_india_timezone(self):
		order = self.create_order()
		timestamp = datetime(2026, 1, 1, 14, 30, tzinfo=datetime_timezone.utc)
		Order.objects.filter(id=order.id).update(created_at=timestamp)
		self.client.force_login(self.staff)

		response = self.client.get(reverse('inventory:staff_orders'))

		self.assertContains(response, '01 Jan 2026, 08:00 PM')

	def test_shared_payment_details_show_requested_number(self):
		response = self.client.get(reverse('inventory:home'))

		self.assertContains(response, '+91 98948 35855')
