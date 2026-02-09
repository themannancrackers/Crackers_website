from django.db import models
from django.core.validators import MinValueValidator
from django.conf import settings

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def _str_(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['order', 'name']

class Product(models.Model):
    name = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    stock_quantity = models.IntegerField(validators=[MinValueValidator(0)])
    description = models.TextField()
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @property
    def is_low_stock(self):
        return self.stock_quantity < 10

class Order(models.Model):
    MIN_ORDER_AMOUNT = 3000  # Minimum order amount in rupees
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders', null=True, blank=True)
    full_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    address = models.TextField()  # Renamed from delivery_address to match form field
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(3000)])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order #{self.id} by {self.full_name}"

    class Meta:
        ordering = ['-created_at']

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    
    @property
    def total(self):
        return self.quantity * self.price

    def __str__(self):
        return f"{self.quantity}x {self.product.name} in Order #{self.order.id}"

    class Meta:
        unique_together = ['order', 'product']
