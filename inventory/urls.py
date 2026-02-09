from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    path('', views.home, name='home'),
    path('update-stock/', views.update_stock, name='update_stock'),
    path('checkout/', views.checkout, name='checkout'),
    path('quick-order-lists/', views.get_quick_order_lists, name='quick_order_lists'),
    path(
    "quick-order/<int:list_id>/checkout/",
    views.quick_order_checkout,
    name="quick_order_checkout"),
    # ✅ Admin dashboard and related routes
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/dashboard-data/', views.dashboard_data, name='dashboard_data'),
    path('update-order-status/<int:order_id>/', views.update_order_status, name='update_order_status'),
    path('order-details/<int:order_id>/', views.order_details, name='order_details'),
    path('filter-orders/<str:status>/', views.filter_orders, name='filter_orders'),
    path('quick-add-stock/', views.quick_add_stock, name='quick_add_stock'),

    # ✅ Staff and Product routes
    path('staff/inventory/', views.staff_inventory, name='staff_inventory'),
    path('products/<int:product_id>/delete/', views.delete_product, name='delete_product'),
    path('products/<int:product_id>/', views.get_product, name='get_product'),

    # ✅ Customer routes
    path('orders/', views.customer_orders, name='customer_orders'),
    path('orders/<int:order_id>/update-address/', views.update_order_address, name='update_order_address'),
    path('orders/<int:order_id>/invoice/', views.generate_invoice, name='generate_invoice'),
    path("about/", views.about, name="about"),
    path("safety/", views.safety, name="safety"),
    path("contact/", views.contact, name="contact"),
    path("myorder/", views.customer_orders, name="customer_orders"),
]
