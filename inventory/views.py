from django.shortcuts import render, redirect
from django.http import JsonResponse, FileResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth import get_user_model
from django.db.models import Count, Sum
from django.utils import timezone
from .models import Product, Category, Order, OrderItem
from accounts.models import CustomUser
from accounts.decorators import admin_required, staff_required, approved_user_required
from django.template.loader import render_to_string
from . import utils
import json
import os
from django.conf import settings
import mimetypes

# =====================================================
# 📁 MEDIA FILE SERVING
# =====================================================

def serve_media(request, path):
    """
    Serve media files directly.
    Handles /media/products/* and other media files even when DEBUG=False
    """
    try:
        file_path = os.path.join(settings.MEDIA_ROOT, path)
        
        # Security: prevent directory traversal attacks
        file_path = os.path.abspath(file_path)
        media_root = os.path.abspath(settings.MEDIA_ROOT)
        
        if not file_path.startswith(media_root):
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        if os.path.exists(file_path) and os.path.isfile(file_path):
            # Determine content type
            content_type, _ = mimetypes.guess_type(file_path)
            if content_type is None:
                content_type = 'application/octet-stream'
            
            # FileResponse handles opening and closing the file automatically
            response = FileResponse(open(file_path, 'rb'), content_type=content_type)
            response['Content-Disposition'] = f'inline; filename="{os.path.basename(file_path)}"'
            response['Content-Length'] = os.path.getsize(file_path)
            return response
        else:
            return JsonResponse({'error': 'File not found'}, status=404)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Media serving error: {str(e)}")
        return JsonResponse({'error': 'Error serving file'}, status=500)


@login_required(login_url='account_login')
def home(request):
    from django.db.models import Prefetch
    
    # Get all active products with their categories
    products = Product.objects.filter(is_active=True).select_related('category')

    # Get categories with prefetched products - prevents N+1 query
    categories_with_products = Category.objects.filter(
        products__is_active=True
    ).distinct().order_by('order', 'name').prefetch_related(
        Prefetch('products', queryset=products)
    )
    
    products_by_category = {cat: list(cat.products.all()) for cat in categories_with_products}

    return render(request, 'inventory/home.html', {
        'products': products,
        'categories': categories_with_products,
        'products_by_category': products_by_category,
        'now': timezone.now()
    })

def about(request):
    return render(request, "inventory/about.html")

def safety(request):
    return render(request, "inventory/safety.html")

def contact(request):
    return render(request, "inventory/contact.html")

def customer_orders(request):
    return render(request, "inventory/customer_orders.html")

from django.views.decorators.http import require_http_methods

@require_http_methods(["POST"])
@login_required(login_url='account_login')
def update_stock(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            quantity = int(data.get('quantity', 0))
            
            product = Product.objects.get(id=product_id)
            if product.stock_quantity >= quantity:
                product.stock_quantity -= quantity
                product.save()
                return JsonResponse({
                    'success': True,
                    'new_stock': product.stock_quantity,
                    'is_low_stock': product.is_low_stock
                })
            return JsonResponse({
                'success': False,
                'error': 'Not enough stock available'
            })
        except (Product.DoesNotExist, ValueError, json.JSONDecodeError):
            return JsonResponse({
                'success': False,
                'error': 'Invalid request'
            })
    return JsonResponse({'success': False, 'error': 'Invalid method'})

from django.db import transaction

@require_http_methods(["GET", "POST"])
@login_required(login_url='account_login')
def checkout(request):
    if request.method == 'GET':
        return JsonResponse({
            'success': False,
            'error': 'Please use POST method for checkout'
        })
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            customer_data = data.get('customerData', {})
            cart_items = data.get('cartItems', {})
            
            # Validate customer data
            required_fields = ['fullName', 'email', 'phone', 'deliveryAddress']
            if not all(field in customer_data and customer_data[field] for field in required_fields):
                return utils.handle_api_error(
                    'validation',
                    'Please fill in all required fields',
                    400
                )

            # Update user profile if requested
            try:
                if request.user.is_authenticated and customer_data.get('updateProfile'):
                    User = get_user_model()
                    user = User.objects.get(id=request.user.id)
                    
                    # Split full name into first_name and last_name
                    full_name = customer_data['fullName'].split(maxsplit=1)
                    user.first_name = full_name[0]
                    user.last_name = full_name[1] if len(full_name) > 1 else ''
                    
                    user.phone_number = customer_data['phone']
                    user.address = customer_data['deliveryAddress']
                    # Don't update email as it might require verification
                    user.save()
            except Exception as profile_error:
                # Log but don't fail checkout
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Profile update failed: {str(profile_error)}")
            
            # Validate cart is not empty
            if not cart_items:
                return utils.handle_api_error(
                    'validation',
                    'Your cart is empty. Please add items before checking out.',
                    400
                )

            # Calculate total amount first
            total_amount = sum(float(item['price']) * item['quantity'] for item in cart_items.values())
            
            # Validate minimum order amount (2500)
            MIN_ORDER_AMOUNT = 2500
            if total_amount < MIN_ORDER_AMOUNT:
                return utils.handle_api_error(
                    'minimum_order',
                    f'Minimum order amount is ₹{MIN_ORDER_AMOUNT}. Current total: ₹{total_amount:.2f}',
                    400,
                    {
                        'minimum_required': MIN_ORDER_AMOUNT,
                        'current_total': total_amount,
                        'shortfall': MIN_ORDER_AMOUNT - total_amount
                    }
                )

            # Start database transaction
            with transaction.atomic():
                # Check stock availability first
                for product_id, item in cart_items.items():
                    try:
                        product = Product.objects.get(id=product_id)
                        if product.stock_quantity < item['quantity']:
                            return utils.handle_api_error(
                                'stock',
                                f'Insufficient stock for {product.name}. Available: {product.stock_quantity}',
                                400
                            )
                    except Product.DoesNotExist:
                        return utils.handle_api_error(
                            'not_found',
                            f'Product with ID {product_id} not found',
                            404
                        )
                
                # Create the order
                order = Order.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    full_name=customer_data['fullName'],
                    address=customer_data['deliveryAddress'],
                    phone=customer_data['phone'],
                    email=customer_data['email'],
                    total_amount=total_amount,
                    status='pending'
                )

                # Create order items
                for product_id, item in cart_items.items():
                    product = Product.objects.get(id=product_id)
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=item['quantity'],
                        price=item['price']
                    )

                # Update stock quantities
                low_stock_products = []
                for product_id, item in cart_items.items():
                    product = Product.objects.get(id=product_id)
                    item_quantity = item.get('quantity', 0)
                    if item_quantity > 0:
                        product.stock_quantity -= item_quantity
                        product.save()
                        
                        # Collect low stock products for batch alert
                        if product.is_low_stock:
                            low_stock_products.append(product)
                
                # Send consolidated batch alert for all low stock items
                if low_stock_products:
                    transaction.on_commit(lambda: utils.send_batch_stock_alerts(low_stock_products))

                order_summary = {
                    'customer': customer_data,
                    'items': cart_items,
                    'total': total_amount,
                    'order_id': order.id
                }

                # Queue confirmation email to be sent after successful transaction
                transaction.on_commit(lambda: utils.send_order_confirmation({
                    'customerData': customer_data,
                    'cartItems': cart_items,
                    'orderId': order.id
                }))

            return JsonResponse({
                'success': True,
                'message': 'Order placed successfully!',
                'orderSummary': order_summary
            })
            
        except json.JSONDecodeError:
            return utils.handle_api_error(
                'validation',
                'Invalid request data format',
                400
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Checkout error: {str(e)}", exc_info=True)
            return utils.handle_api_error(
                'server',
                'An unexpected error occurred during checkout. Please try again later.',
                500
            )
            
    return utils.handle_api_error(
        'validation',
        'Invalid request method',
        405
    )

@admin_required
@login_required(login_url='account_login')
@admin_required
def admin_dashboard(request):
    context = {
        'total_users': CustomUser.objects.count(),
        'total_products': Product.objects.count(),
        'total_orders': Order.objects.count(),
        'total_revenue': Order.objects.filter(status='delivered').aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
        'recent_orders': Order.objects.order_by('-created_at')[:10],
        'low_stock_products': Product.objects.filter(stock_quantity__lt=10)
    }
    return render(request, 'inventory/admin_dashboard.html', context)

@admin_required
def dashboard_data(request):
    data = {
        'total_users': CustomUser.objects.count(),
        'total_products': Product.objects.count(),
        'total_orders': Order.objects.count(),
        'total_revenue': Order.objects.filter(status='delivered').aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
        'recent_orders': list(Order.objects.order_by('-created_at')[:10].values(
            'id', 'full_name', 'total_amount', 'status'
        )),
        'low_stock_products': list(Product.objects.filter(stock_quantity__lt=10).values(
            'id', 'name', 'stock_quantity'
        ))
    }
    
    # Add status choices for each order
    for order in data['recent_orders']:
        order['status_choices'] = Order.STATUS_CHOICES
    
    return JsonResponse(data)

@admin_required
def update_order_status(request, order_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            order = Order.objects.get(id=order_id)
            order.status = data['status']
            order.save()
            return JsonResponse({'success': True})
        except (Order.DoesNotExist, KeyError, json.JSONDecodeError):
            return JsonResponse({'success': False})
    return JsonResponse({'success': False})

@admin_required
def order_details(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
        items = order.items.select_related('product').all()
        html = render_to_string('inventory/order_details.html', {
            'order': order,
            'items': items
        })
        return JsonResponse({'success': True, 'html': html})
    except Order.DoesNotExist:
        return JsonResponse({'success': False})

@admin_required
def filter_orders(request, status):
    if status == 'all':
        orders = Order.objects.all()
    else:
        orders = Order.objects.filter(status=status)
    
    orders = orders.order_by('-created_at')[:10].values(
        'id', 'full_name', 'total_amount', 'status'
    )
    return JsonResponse({
        'success': True,
        'orders': list(orders)
    })

@admin_required
def quick_add_stock(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product = Product.objects.get(id=data['product_id'])
            product.stock_quantity += int(data['quantity'])
            product.save()
            return JsonResponse({'success': True})
        except (Product.DoesNotExist, KeyError, ValueError, json.JSONDecodeError):
            return JsonResponse({'success': False})
    return JsonResponse({'success': False})

@staff_required
@login_required(login_url='account_login')
@staff_required
def staff_inventory(request):
    if request.method == 'POST':
        try:
            data = request.POST
            product_id = data.get('product_id')
            image = request.FILES.get('image')
            
            if product_id:  # Edit existing product
                product = Product.objects.get(id=product_id)
                product.name = data['name']
                product.category_id = data['category']
                product.price = data['price']
                product.stock_quantity = data['stock_quantity']
                if image:
                    product.image = image
                product.save()
            else:  # Create new product
                product = Product.objects.create(
                    name=data['name'],
                    category_id=data['category'],
                    price=data['price'],
                    stock_quantity=data['stock_quantity'],
                    image=image
                )
            return JsonResponse({
                'success': True,
                'product_id': product.id,
                'message': 'Product updated successfully' if product_id else 'Product created successfully'
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    # Handle search
    search_query = request.GET.get('search', '')
    products = Product.objects.all()
    
    if search_query:
        products = products.filter(name__icontains=search_query)
    
    products = products.order_by('category', 'name')
    
    context = {
        'products': products,
        'categories': Category.objects.all(),
        'search_query': search_query
    }
    return render(request, 'inventory/staff_inventory.html', context)

@require_http_methods(["DELETE"])
@staff_required
def delete_product(request, product_id):
    try:
        product = Product.objects.get(id=product_id)
        product.delete()
        return JsonResponse({'success': True})
    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Product not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@staff_required
@login_required(login_url='account_login')
@staff_required
def get_product(request, product_id):
    try:
        product = Product.objects.get(id=product_id)
        return JsonResponse({
            'success': True,
            'product': {
                'id': product.id,
                'name': product.name,
                'category': product.category_id,
                'price': product.price,
                'stock_quantity': product.stock_quantity,
                'image_url': product.image.url if product.image else None
            }
        })
    except Product.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Product not found'
        })

from django.http import HttpResponse
from io import BytesIO
from django.utils import timezone
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

@login_required(login_url='account_login')
@approved_user_required
def update_order_address(request, order_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            order = Order.objects.get(id=order_id, user=request.user)
            order.address = data['delivery_address']
            order.save()
            return JsonResponse({'success': True})
        except (Order.DoesNotExist, KeyError, json.JSONDecodeError):
            return JsonResponse({'success': False})
    return JsonResponse({'success': False})

@login_required(login_url='account_login')
@approved_user_required
def customer_orders(request):
    # Get orders with related items and products
    orders = Order.objects.filter(user=request.user).prefetch_related(
        'items__product'
    ).order_by('-created_at')
    
    # Add status colors and process order information
    for order in orders:
        # Status colors
        if order.status == 'pending':
            order.status_color = 'warning'
        elif order.status == 'processing':
            order.status_color = 'info'
        elif order.status == 'shipped':
            order.status_color = 'primary'
        elif order.status == 'delivered':
            order.status_color = 'success'
        elif order.status == 'cancelled':
            order.status_color = 'danger'
        
        # Calculate order statistics
        order.total_items = sum(item.quantity for item in order.items.all())
        order.shipping_status = get_shipping_status(order)
    
    context = {
        'orders': orders,
        'total_orders': len(orders),
        'total_spent': sum(order.total_amount for order in orders if order.status == 'delivered'),
        'pending_orders': sum(1 for order in orders if order.status == 'pending'),
        'recent_order': orders.first() if orders else None,
    }
    
    return render(request, 'inventory/customer_orders.html', context)

def get_shipping_status(order):
    status_info = {
        'pending': {
            'message': 'Order received, awaiting confirmation',
            'progress': 20,
            'icon': 'bi-box'
        },
        'processing': {
            'message': 'Order is being processed',
            'progress': 40,
            'icon': 'bi-gear'
        },
        'shipped': {
            'message': 'Order has been shipped',
            'progress': 60,
            'icon': 'bi-truck'
        },
        'delivered': {
            'message': 'Order delivered successfully',
            'progress': 100,
            'icon': 'bi-check-circle'
        },
        'cancelled': {
            'message': 'Order has been cancelled',
            'progress': 0,
            'icon': 'bi-x-circle'
        }
    }
    return status_info.get(order.status, {})

@login_required
@approved_user_required
@login_required(login_url='account_login')
def generate_invoice(request, order_id):
    try:
        order = Order.objects.get(id=order_id, user=request.user)
        items = order.items.select_related('product').all()
        
        # Create PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=1  # Center alignment
        )
        elements.append(Paragraph("INVOICE", title_style))
        elements.append(Paragraph("The Mannan Crackers", styles['Heading2']))
        elements.append(Spacer(1, 20))
        
        # Order Info
        order_info = [
            [Paragraph(f"<b>Date:</b> {order.created_at.strftime('%B %d, %Y')}", styles['Normal']),
             Paragraph(f"<b>Status:</b> {order.get_status_display()}", styles['Normal'])],
            [Paragraph(f"<b>Customer:</b> {order.full_name}", styles['Normal']),
             ''],
            [Paragraph(f"<b>Phone:</b> {order.phone}", styles['Normal']),
             Paragraph(f"<b>Email:</b> {order.email}", styles['Normal'])],
            [Paragraph(f"<b>Shipping Address:</b> {order.address}", styles['Normal']), '']
        ]
        
        order_table = Table(order_info, colWidths=[4*inch, 4*inch])
        order_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -2), 1, colors.black),
            ('BOX', (0, 0), (-1, -1), 2, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ]))
        elements.append(order_table)
        elements.append(Spacer(1, 20))
        
        # Items Table
        items_data = [['Product', 'Quantity', 'Price', 'Total']]
        for item in items:
            items_data.append([
                item.product.name,
                str(item.quantity),
                f"₹{item.price}",
                f"₹{item.total}"
            ])
        items_data.append(['', '', 'Total Amount:', f"₹{order.total_amount}"])
        
        items_table = Table(items_data, colWidths=[4*inch, 1.5*inch, 1.5*inch, 1*inch])
        items_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -2), 1, colors.black),
            ('BOX', (0, 0), (-1, -1), 2, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('ALIGN', (-2, -1), (-1, -1), 'RIGHT'),
        ]))
        elements.append(items_table)
        
        # Footer
        elements.append(Spacer(1, 30))
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.grey,
            alignment=1
        )
        elements.append(Paragraph("Thank you for shopping with The Mannan Crackers!", footer_style))
        elements.append(Paragraph(f"Generated on: {timezone.now().strftime('%B %d, %Y %H:%M')}", footer_style))
        
        # Build PDF
        doc.build(elements)
        
        # Prepare response
        pdf = buffer.getvalue()
        buffer.close()
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice-{order.id}.pdf"'
        
        return response
        
    except Order.DoesNotExist:
        return HttpResponse("Order not found", status=404)


# =====================================================
# 🔴 ERROR HANDLERS
# =====================================================

def error_page(request, error_code='500', error_title='Oops! Something went wrong', 
               error_message='We encountered an unexpected error. Please try again later.', 
               error_details=''):
    """Generic error page handler"""
    context = {
        'error_code': error_code,
        'error_title': error_title,
        'error_message': error_message,
        'error_details': error_details,
    }
    return render(request, 'error.html', context, status=int(error_code.split()[0]) if error_code[0].isdigit() else 500)


def handle_404(request, exception=None):
    """Handle 404 Page Not Found errors"""
    return error_page(
        request,
        error_code='404',
        error_title='Page Not Found',
        error_message='The page you\'re looking for doesn\'t exist or has been moved. Let\'s get you back on track!',
        error_details='The requested URL could not be found on this server.'
    )


def handle_500(request):
    """Handle 500 Internal Server errors"""
    return error_page(
        request,
        error_code='500',
        error_title='Internal Server Error',
        error_message='Our servers encountered an issue while processing your request. Our team has been notified!',
        error_details='An unexpected error occurred. Please try refreshing the page or come back later.'
    )


def handle_403(request, exception=None):
    """Handle 403 Permission Denied errors"""
    return error_page(
        request,
        error_code='403',
        error_title='Access Denied',
        error_message='You don\'t have permission to access this resource.',
        error_details='If you believe this is an error, please contact support.'
    )


def handle_400(request, exception=None):
    """Handle 400 Bad Request errors"""
    return error_page(
        request,
        error_code='400',
        error_title='Bad Request',
        error_message='The server couldn\'t understand your request. Please try again with valid data.',
        error_details='The request sent to the server was invalid or malformed.'
    )


def handle_connection_error(request):
    """Handle connection/network errors"""
    return error_page(
        request,
        error_code='connection',
        error_title='Connection Error',
        error_message='It seems we\'re having trouble connecting to our servers. This might be a network issue.',
        error_details='Check your internet connection and try again.'
    )


def handle_maintenance(request):
    """Handle maintenance mode"""
    return error_page(
        request,
        error_code='503',
        error_title='Under Maintenance',
        error_message='We\'re currently performing maintenance. We\'ll be back online soon!',
        error_details='Thank you for your patience. Check back in a few moments.'
    )


# =====================================================
# ⚡ QUICK ORDER SYSTEM
# =====================================================

@login_required(login_url='account_login')
def get_quick_order_lists(request):
    """Get predefined quick order lists with products from all categories"""
    try:
        # Get all active products grouped by category
        products = Product.objects.filter(is_active=True).select_related('category')
        
        # Define 5 comprehensive cracker lists
        quick_order_lists = [
            {
                'id': 1,
                'name': '🎆 Premium Diwali Package',
                'description': 'Best-seller assortment with premium selections from all categories',
                'emoji': '🎆',
                'color': '#ff6b35',
                'products_query': 'premium|deluxe|special|gold',
                'min_categories': 3,
                'price_range': 'mixed',
            },
            {
                'id': 2,
                'name': '👨‍👩‍👧‍👦 Family Celebration Pack',
                'description': 'Perfect for family gatherings - safe for kids and adults',
                'emoji': '👨‍👩‍👧‍👦',
                'color': '#4b0082',
                'category_focus': ['Flower Pots', 'Chakkar', 'Sparklers', 'Colour Fountain Big'],
            },
            {
                'id': 3,
                'name': '👦 Kids Delight Collection',
                'description': 'Fun and safe crackers for boys and girls',
                'emoji': '👦',
                'color': '#ff69b4',
                'category_focus': ['Spinner', 'Baby Fancy Novelties', 'Flower Pots', 'Mega Wonder Fountain (Window)'],
            },
            {
                'id': 4,
                'name': '✨ Festive Sparkler Set',
                'description': 'Beautiful sparklers and flower pots for stunning displays',
                'emoji': '✨',
                'color': '#ffd700',
                'products_query': 'sparkler|flower|pot|fountain',
            },
            {
                'id': 5,
                'name': '🎉 Grand Celebration Bundle',
                'description': 'Ultimate assortment - everything for a complete celebration',
                'emoji': '🎉',
                'color': '#28a745',
                'premium': True,
            },
        ]
        
        # Populate lists with actual products ensuring minimum price per list
        # Default minimum is ₹2500, but Family Celebration Pack & Kids Delight Collection require ₹3500
        MIN_PACK_AMOUNTS = {
            1: 2500,  # Premium Diwali Package
            2: 3500,  # Family Celebration Pack
            3: 3500,  # Kids Delight Collection
            4: 2500,  # Festive Sparkler Set
            5: 2500,  # Grand Celebration Bundle
        }
        
        # Get all products sorted by price descending for better selection
        all_products_sorted = Product.objects.filter(is_active=True).order_by('-price')
        
        for quick_list in quick_order_lists:
            MIN_PACK_AMOUNT = MIN_PACK_AMOUNTS.get(quick_list['id'], 2500)
            selected_products = []
            list_total = 0
            
            # Strategy: Select high-value products first to quickly reach minimum
            # Then add variety with different price points
            if quick_list['id'] == 2:  # Family Celebration Pack
                # Get from Flower Pots, Chakkar, Sparklers, Fountains
                for category_name in ['Flower Pots', 'Chakkar', 'Colour Fountain Big', 'Sparklers', 'Mega Wonder Fountain (Window)']:
                    if list_total >= MIN_PACK_AMOUNT and len(selected_products) >= 6:
                        break
                    cat_products = Product.objects.filter(
                        is_active=True,
                        category__name=category_name
                    ).order_by('-price')[:10]  # Take top 10 most expensive from each category
                    for p in cat_products:
                        if list_total >= MIN_PACK_AMOUNT and len(selected_products) >= 6:
                            break
                        if p not in selected_products:
                            selected_products.append(p)
                            list_total += float(p.price)
                            
            elif quick_list['id'] == 3:  # Kids Delight Collection
                # Get from kid-friendly categories
                for category_name in ['Spinner', 'Flower Pots', 'Chakkar', 'Mega Wonder Fountain (Window)', 'Colour Fountain Big']:
                    if list_total >= MIN_PACK_AMOUNT and len(selected_products) >= 6:
                        break
                    cat_products = Product.objects.filter(
                        is_active=True,
                        category__name=category_name
                    ).order_by('-price')[:10]
                    for p in cat_products:
                        if list_total >= MIN_PACK_AMOUNT and len(selected_products) >= 6:
                            break
                        if p not in selected_products:
                            selected_products.append(p)
                            list_total += float(p.price)
                            
            elif quick_list['id'] == 4:  # Festive Sparkler Set
                # Focus on Sparklers and related categories
                for category_name in ['Sparklers', 'Peacock Varieties', 'New Fancy']:
                    if list_total >= MIN_PACK_AMOUNT and len(selected_products) >= 4:
                        break
                    cat_products = Product.objects.filter(
                        is_active=True,
                        category__name=category_name
                    ).order_by('-price')[:10]
                    for p in cat_products:
                        if list_total >= MIN_PACK_AMOUNT and len(selected_products) >= 4:
                            break
                        if p not in selected_products:
                            selected_products.append(p)
                            list_total += float(p.price)
            else:
                # For other lists, select high-value products from all categories
                for p in all_products_sorted:
                    if list_total >= MIN_PACK_AMOUNT:
                        # Ensure minimum variety
                        if (quick_list['id'] in [2, 3] and len(selected_products) >= 6) or len(selected_products) >= 4:
                            break
                    selected_products.append(p)
                    list_total += float(p.price)
            
            # Ensure we have enough products for variety
            min_products = 6 if quick_list['id'] in [2, 3] else 4
            if len(selected_products) < min_products:
                for p in all_products_sorted:
                    if p not in selected_products and len(selected_products) < min_products:
                        selected_products.append(p)
                        list_total += float(p.price)
            
            # Ensure minimum total is met
            if list_total < MIN_PACK_AMOUNT:
                for p in all_products_sorted:
                    if p not in selected_products and list_total < MIN_PACK_AMOUNT:
                        selected_products.append(p)
                        list_total += float(p.price)
            
            # Format products for response
            quick_list['products'] = [
                {
                    'id': p.id,
                    'name': p.name,
                    'price': float(p.price),
                    'category': p.category.name,
                    'image_url': p.image.url if p.image else None,
                    'quantity': 1,
                }
                for p in selected_products
            ]
            
            # Calculate and set total
            quick_list['total'] = sum(p['price'] * p['quantity'] for p in quick_list['products'])
            quick_list['item_count'] = len(quick_list['products'])
        
        return JsonResponse({
            'success': True,
            'quick_order_lists': quick_order_lists
        })
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error fetching quick order lists: {str(e)}")
        return utils.handle_api_error(
            'server',
            'Failed to load quick order lists',
            500
        )


@login_required(login_url='account_login')
def quick_order_checkout(request, list_id):
    """Handle quick order checkout - adds predefined list to cart and proceeds to checkout"""
    if request.method != 'POST':
        return utils.handle_api_error('validation', 'Invalid request method', 405)
    
    try:
        data = json.loads(request.body)
        products_data = data.get('products', [])
        
        if not products_data:
            return utils.handle_api_error(
                'validation',
                'No products selected',
                400
            )
        
        # Verify product availability and get product details
        cart_items = {}
        total_amount = 0
        
        for item in products_data:
            try:
                product = Product.objects.get(id=item['id'], is_active=True)
                
                if product.stock_quantity < item.get('quantity', 1):
                    return utils.handle_api_error(
                        'stock',
                        f'Insufficient stock for {product.name}',
                        400
                    )
                
                quantity = item.get('quantity', 1)
                item_total = float(product.price) * quantity
                total_amount += item_total
                
                cart_items[str(product.id)] = {
                    'name': product.name,
                    'quantity': quantity,
                    'price': float(product.price)
                }
                
            except Product.DoesNotExist:
                return utils.handle_api_error(
                    'not_found',
                    f'Product not found',
                    404
                )
        
        # Check minimum order amount
        MIN_ORDER_AMOUNT = 2500
        if total_amount < MIN_ORDER_AMOUNT:
            return utils.handle_api_error(
                'minimum_order',
                f'Minimum order amount is ₹{MIN_ORDER_AMOUNT}. Current total: ₹{total_amount:.2f}',
                400,
                {
                    'minimum_required': MIN_ORDER_AMOUNT,
                    'current_total': total_amount,
                    'shortfall': MIN_ORDER_AMOUNT - total_amount,
                    'cart_items': cart_items,
                    'list_id': list_id
                }
            )
        
        # Return cart data for frontend to populate
        return JsonResponse({
            'success': True,
            'message': 'Quick order added to cart successfully',
            'cart_items': cart_items,
            'total_amount': total_amount,
            'list_id': list_id,
            'ready_for_checkout': True
        })
        
    except json.JSONDecodeError:
        return utils.handle_api_error('validation', 'Invalid JSON data', 400)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Quick order checkout error: {str(e)}")
        return utils.handle_api_error(
            'server',
            'Error processing quick order',
            500
        )
